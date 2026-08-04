"""
EventFormatter — converts a BaseEvent into channel-specific message strings.

Each channel has different formatting requirements:
- Telegram: MarkdownV2 (escape special chars, support bold/mono)
- Discord:  JSON embed object
- Email:    HTML body + plain-text fallback

Keeping formatting here (not inside each channel) means channel code stays
thin and formatting logic is testable without HTTP calls.
"""
import re
from dataclasses import dataclass

from app.events.types import BaseEvent, EventType

# Maps event type → emoji prefix for quick visual scanning
_EVENT_EMOJI: dict[str, str] = {
    EventType.WHALE_BUY: "🐋",
    EventType.WHALE_SELL: "🔴",
    EventType.EXCHANGE_DEPOSIT: "🏦",
    EventType.EXCHANGE_WITHDRAWAL: "🏧",
    EventType.LIQUIDITY_ADDED: "💧",
    EventType.LIQUIDITY_REMOVED: "🌊",
    EventType.CONTRACT_DEPLOYMENT: "📄",
    EventType.TOKEN_MINT: "🪙",
    EventType.TOKEN_BURN: "🔥",
    EventType.LARGE_SWAP: "🔄",
    EventType.SMART_MONEY_ACTIVITY: "🧠",
    EventType.WALLET_ACCUMULATION: "📈",
    EventType.WALLET_DISTRIBUTION: "📉",
}

_EVENT_LABEL: dict[str, str] = {
    EventType.WHALE_BUY: "Whale Buy",
    EventType.WHALE_SELL: "Whale Sell",
    EventType.EXCHANGE_DEPOSIT: "Exchange Deposit",
    EventType.EXCHANGE_WITHDRAWAL: "Exchange Withdrawal",
    EventType.LIQUIDITY_ADDED: "Liquidity Added",
    EventType.LIQUIDITY_REMOVED: "Liquidity Removed",
    EventType.CONTRACT_DEPLOYMENT: "Contract Deployment",
    EventType.TOKEN_MINT: "Token Mint",
    EventType.TOKEN_BURN: "Token Burn",
    EventType.LARGE_SWAP: "Large Swap",
    EventType.SMART_MONEY_ACTIVITY: "Smart Money",
    EventType.WALLET_ACCUMULATION: "Accumulation",
    EventType.WALLET_DISTRIBUTION: "Distribution",
}

_ETHERSCAN_TX = "https://etherscan.io/tx/{}"
_ETHERSCAN_ADDR = "https://etherscan.io/address/{}"


def _escape_markdown_v2(text: str) -> str:
    """Escape all MarkdownV2 reserved characters."""
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!\\])", r"\\\1", text)


@dataclass(frozen=True)
class FormattedMessage:
    title: str
    body_text: str       # plain text (Telegram, fallback)
    body_html: str       # HTML (email)
    discord_embed: dict  # Discord embed payload


class EventFormatter:
    def format(self, event: BaseEvent) -> FormattedMessage:
        emoji = _EVENT_EMOJI.get(event.event_type, "⚡")
        label = _EVENT_LABEL.get(event.event_type, event.event_type)
        usd = f"${float(event.usd_value):,.0f}"
        short_wallet = f"{event.wallet_address[:6]}…{event.wallet_address[-4:]}"
        short_tx = f"{event.tx_hash[:10]}…"
        tx_url = _ETHERSCAN_TX.format(event.tx_hash)
        addr_url = _ETHERSCAN_ADDR.format(event.wallet_address)

        title = f"{emoji} {label} — {event.token_symbol}"

        body_text = (
            f"{emoji} *{label}* — {event.token_symbol}\n"
            f"💰 {usd}\n"
            f"📍 [{short_wallet}]({addr_url})\n"
            f"🔗 [Tx {short_tx}]({tx_url})\n"
            f"ℹ️ {event.explanation}\n"
            f"⚡ Confidence: {event.confidence_score:.0%}"
        )

        body_html = f"""
<html><body style="font-family:sans-serif;background:#0D1117;color:#fff;padding:24px">
  <h2 style="color:#00E5FF">{emoji} {label} — {event.token_symbol}</h2>
  <table style="border-collapse:collapse;width:100%">
    <tr><td style="padding:6px;color:#8b949e">Amount</td>
        <td style="padding:6px;font-weight:bold">{usd}</td></tr>
    <tr><td style="padding:6px;color:#8b949e">Wallet</td>
        <td style="padding:6px"><a href="{addr_url}" style="color:#00E5FF">{short_wallet}</a></td></tr>
    <tr><td style="padding:6px;color:#8b949e">Transaction</td>
        <td style="padding:6px"><a href="{tx_url}" style="color:#00E5FF">{short_tx}</a></td></tr>
    <tr><td style="padding:6px;color:#8b949e">Confidence</td>
        <td style="padding:6px">{event.confidence_score:.0%}</td></tr>
  </table>
  <p style="color:#8b949e;margin-top:16px">{event.explanation}</p>
  <p style="color:#30363d;font-size:12px">PumpWatch — pumpwat.ch</p>
</body></html>
"""

        discord_embed = {
            "title": title,
            "description": event.explanation,
            "color": _discord_color(event.event_type),
            "fields": [
                {"name": "Amount", "value": usd, "inline": True},
                {"name": "Token", "value": event.token_symbol, "inline": True},
                {"name": "Confidence", "value": f"{event.confidence_score:.0%}", "inline": True},
                {"name": "Wallet", "value": f"[{short_wallet}]({addr_url})", "inline": False},
                {"name": "Transaction", "value": f"[{short_tx}]({tx_url})", "inline": False},
            ],
            "footer": {"text": "PumpWatch • pumpwat.ch"},
            "timestamp": event.timestamp.isoformat(),
        }

        return FormattedMessage(
            title=title,
            body_text=body_text,
            body_html=body_html,
            discord_embed=discord_embed,
        )


def _discord_color(event_type: str) -> int:
    """Discord embed sidebar color as an integer."""
    colors = {
        EventType.WHALE_BUY: 0x00E5FF,
        EventType.WHALE_SELL: 0xFF3D00,
        EventType.EXCHANGE_DEPOSIT: 0xFFD600,
        EventType.EXCHANGE_WITHDRAWAL: 0xFFD600,
        EventType.TOKEN_MINT: 0x00C853,
        EventType.TOKEN_BURN: 0xFF3D00,
        EventType.LARGE_SWAP: 0x00B8D4,
        EventType.SMART_MONEY_ACTIVITY: 0xAA00FF,
        EventType.WALLET_ACCUMULATION: 0x00C853,
        EventType.WALLET_DISTRIBUTION: 0xFF3D00,
    }
    return colors.get(event_type, 0x00E5FF)
