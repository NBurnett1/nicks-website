#!/usr/bin/env python3
"""
Send weekly picks email to all subscribers.
Reads ENCRYPTED subscribers from subscribers.json and decrypts them,
then sends a formatted HTML email with the current week's picks via Gmail SMTP.

Required environment variables:
  GMAIL_USER         — Gmail address (e.g. nick@gmail.com)
  GMAIL_APP_PASSWORD — Gmail App Password (NOT your regular password)
  ENCRYPT_KEY        — Shared encryption key (same as Vercel env var)

Run: python scripts/send_weekly_email.py
"""

import json
import os
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def decrypt_email(encrypted_str, key_str):
    """Decrypt an AES-256-GCM encrypted email."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = hashlib.sha256(key_str.encode()).digest()
    parts = encrypted_str.split(':')
    if len(parts) != 3:
        return None

    iv = bytes.fromhex(parts[0])
    ciphertext = bytes.fromhex(parts[1])
    tag = bytes.fromhex(parts[2])

    aesgcm = AESGCM(key)
    # GCM expects ciphertext + tag concatenated
    plaintext = aesgcm.decrypt(iv, ciphertext + tag, None)
    return plaintext.decode('utf-8')


def load_subscribers():
    """Load and decrypt subscriber list from repo."""
    encrypt_key = os.environ.get('ENCRYPT_KEY')
    path = os.path.join(os.path.dirname(__file__), '..', 'subscribers.json')

    if not os.path.exists(path):
        print("  ⚠ No subscribers.json found")
        return []

    with open(path) as f:
        data = json.load(f)

    entries = data.get('entries', [])
    if not entries:
        # Fallback: try old plaintext format
        emails = data.get('emails', [])
        if emails:
            print(f"  📧 {len(emails)} subscribers loaded (plaintext fallback)")
            return emails
        print("  ⚠ No subscribers found")
        return []

    if not encrypt_key:
        print("  ⚠ ENCRYPT_KEY not set — cannot decrypt subscribers")
        return []

    emails = []
    for entry in entries:
        try:
            email = decrypt_email(entry['data'], encrypt_key)
            if email:
                emails.append(email)
        except Exception as e:
            print(f"  ⚠ Failed to decrypt entry: {e}")

    print(f"  📧 {len(emails)} subscribers decrypted")
    return emails


def load_current_week():
    """Load the current active week's picks."""
    weeks_dir = os.path.join(os.path.dirname(__file__), '..', 'public', 'data', 'weeks')
    index_path = os.path.join(weeks_dir, 'index.json')
    if not os.path.exists(index_path):
        return None, None

    with open(index_path) as f:
        index = json.load(f)

    weeks = index.get('weeks', [])
    if not weeks:
        return None, None

    # Get the latest week
    latest = max(weeks, key=lambda w: w['week'])
    week_path = os.path.join(weeks_dir, f"week{latest['week']}.json")
    if not os.path.exists(week_path):
        return None, None

    with open(week_path) as f:
        week_data = json.load(f)

    # Try to load macro context
    macro_path = os.path.join(weeks_dir, f"week{latest['week']}_macro.json")
    macro = None
    if os.path.exists(macro_path):
        with open(macro_path) as f:
            macro = json.load(f)

    return week_data, macro


def build_email_html(week_data, macro):
    """Build a clean HTML email with the week's picks."""
    week_num = week_data['week']
    start = week_data.get('startDate', '')
    end = week_data.get('endDate', '')
    picks = week_data.get('picks', [])
    status = week_data.get('status', 'active')

    # Format dates
    try:
        start_fmt = datetime.strptime(start, '%Y-%m-%d').strftime('%d %b')
        end_fmt = datetime.strptime(end, '%Y-%m-%d').strftime('%d %b %Y')
        date_range = f"{start_fmt} – {end_fmt}"
    except:
        date_range = f"{start} – {end}"

    # Subject line
    if status == 'active':
        subject = f"🟢 Week {week_num} Picks Are Live — {date_range}"
    else:
        avg_pnl = week_data.get('summary', {}).get('avgPnlPct', 0)
        emoji = '📈' if avg_pnl >= 0 else '📉'
        subject = f"{emoji} Week {week_num} Results: {avg_pnl:+.1f}% — {date_range}"

    # Build picks HTML
    picks_html = ""
    for i, pick in enumerate(picks):
        ticker = pick.get('ticker', '?')
        name = pick.get('name', '')
        grade = pick.get('grade', '?')
        tests = pick.get('testsPassed', 0)
        entry = pick.get('entryPrice', 0)
        pnl_pct = pick.get('pnlPct', 0)
        thesis = pick.get('thesis', '')
        pick_type = pick.get('type', 'core')
        sector = pick.get('sector', '')

        # Color coding
        if pnl_pct > 0:
            pnl_color = '#10b981'
            pnl_text = f'+{pnl_pct:.1f}%'
        elif pnl_pct < 0:
            pnl_color = '#ef4444'
            pnl_text = f'{pnl_pct:.1f}%'
        else:
            pnl_color = '#94a3b8'
            pnl_text = '—'

        grade_colors = {'A': '#10b981', 'B': '#5eead4', 'C': '#fbbf24', 'D': '#f87171'}
        grade_color = grade_colors.get(grade, '#94a3b8')

        badge = ' 🎲' if pick_type == 'speculative' else ''
        stop_html = ''
        if pick.get('stopTriggered'):
            stop_html = f'<span style="color:#ef4444;font-size:12px;"> 🛑 {pick["stopTriggered"]}</span>'

        picks_html += f"""
        <tr style="border-bottom:1px solid #1e293b;">
          <td style="padding:14px 12px;">
            <div style="font-weight:800;font-size:16px;color:#f1f5f9;">{ticker}{badge}</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:2px;">{name}</div>
            <div style="font-size:11px;color:#64748b;margin-top:2px;">{sector}</div>
          </td>
          <td style="padding:14px 8px;text-align:center;">
            <span style="background:rgba({grade_color},0.15);color:{grade_color};font-weight:800;padding:4px 10px;border-radius:6px;font-size:14px;">
              {grade}
            </span>
            <div style="font-size:11px;color:#64748b;margin-top:4px;">{tests}/8</div>
          </td>
          <td style="padding:14px 8px;text-align:center;font-weight:600;color:#f1f5f9;">
            A${entry:.2f}
          </td>
          <td style="padding:14px 8px;text-align:center;font-weight:800;color:{pnl_color};font-size:15px;">
            {pnl_text}{stop_html}
          </td>
        </tr>
        <tr>
          <td colspan="4" style="padding:0 12px 12px;font-size:12px;color:#94a3b8;line-height:1.5;">
            {thesis}
          </td>
        </tr>
        """

    # Macro context
    macro_html = ""
    if macro:
        headline = macro.get('headline', '')
        themes = macro.get('themes', [])
        if headline:
            themes_html = ''.join(f'<li style="color:#94a3b8;font-size:13px;margin-bottom:4px;">{t}</li>' for t in themes[:4])
            macro_html = f"""
            <div style="background:rgba(59,130,246,0.06);border:1px solid rgba(59,130,246,0.15);border-radius:12px;padding:16px 20px;margin-bottom:24px;">
              <div style="font-weight:700;color:#f1f5f9;font-size:14px;margin-bottom:8px;">🌍 {headline}</div>
              <ul style="margin:0;padding-left:18px;">{themes_html}</ul>
            </div>
            """

    # Summary stats
    summary = week_data.get('summary', {})
    avg_pnl = summary.get('avgPnlPct', 0)
    winners = summary.get('winners', 0)
    losers = summary.get('losers', 0)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
    <body style="margin:0;padding:0;background:#0a0e1a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
      <div style="max-width:600px;margin:0 auto;padding:24px 16px;">

        <!-- Header -->
        <div style="text-align:center;margin-bottom:24px;">
          <div style="font-size:24px;font-weight:900;color:#f1f5f9;letter-spacing:-0.02em;">
            Nick Knows Best
          </div>
          <div style="font-size:13px;color:#64748b;margin-top:4px;">
            Week {week_num} · {date_range}
          </div>
        </div>

        {macro_html}

        <!-- Summary -->
        <div style="display:flex;gap:12px;margin-bottom:24px;text-align:center;">
          <div style="flex:1;background:#111827;border:1px solid #1e293b;border-radius:12px;padding:12px;">
            <div style="font-size:20px;font-weight:800;color:{'#10b981' if avg_pnl >= 0 else '#ef4444'};">
              {'+' if avg_pnl >= 0 else ''}{avg_pnl:.1f}%
            </div>
            <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-top:2px;">Avg Return</div>
          </div>
          <div style="flex:1;background:#111827;border:1px solid #1e293b;border-radius:12px;padding:12px;">
            <div style="font-size:20px;font-weight:800;color:#10b981;">{winners}</div>
            <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-top:2px;">Winners</div>
          </div>
          <div style="flex:1;background:#111827;border:1px solid #1e293b;border-radius:12px;padding:12px;">
            <div style="font-size:20px;font-weight:800;color:#ef4444;">{losers}</div>
            <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-top:2px;">Losers</div>
          </div>
        </div>

        <!-- Picks Table -->
        <div style="background:#111827;border:1px solid #1e293b;border-radius:12px;overflow:hidden;">
          <table style="width:100%;border-collapse:collapse;">
            <thead>
              <tr style="border-bottom:1px solid #1e293b;">
                <th style="padding:12px;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Stock</th>
                <th style="padding:12px;text-align:center;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Grade</th>
                <th style="padding:12px;text-align:center;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Entry</th>
                <th style="padding:12px;text-align:center;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">P&L</th>
              </tr>
            </thead>
            <tbody>
              {picks_html}
            </tbody>
          </table>
        </div>

        <!-- Footer -->
        <div style="text-align:center;margin-top:32px;padding-top:24px;border-top:1px solid #1e293b;">
          <div style="font-size:12px;color:#64748b;line-height:1.6;">
            This is not financial advice. Always do your own research.<br>
            <a href="https://nicks-website.vercel.app" style="color:#3b82f6;text-decoration:none;">View full dashboard →</a>
          </div>
          <div style="font-size:11px;color:#475569;margin-top:12px;">
            You received this because you subscribed at nickknowsbest.com<br>
            Reply "unsubscribe" to stop receiving these emails.
          </div>
        </div>
      </div>
    </body>
    </html>
    """

    return subject, html


def send_emails(subscribers, subject, html):
    """Send the email to all subscribers via Gmail SMTP."""
    gmail_user = os.environ.get('GMAIL_USER')
    gmail_pass = os.environ.get('GMAIL_APP_PASSWORD')

    if not gmail_user or not gmail_pass:
        print("  ⚠ GMAIL_USER or GMAIL_APP_PASSWORD not set — skipping email send")
        print(f"  📝 Would have sent to {len(subscribers)} subscribers")
        print(f"  📝 Subject: {subject}")
        return

    sent = 0
    failed = 0

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(gmail_user, gmail_pass)

        for email in subscribers:
            try:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = f"Nick Knows Best <{gmail_user}>"
                msg['To'] = email

                # Plain text fallback
                plain = f"New weekly picks are live! Visit https://nicks-website.vercel.app to see them."
                msg.attach(MIMEText(plain, 'plain'))
                msg.attach(MIMEText(html, 'html'))

                server.sendmail(gmail_user, email, msg.as_string())
                sent += 1
                print(f"    ✓ Sent to {email}")
            except Exception as e:
                failed += 1
                print(f"    ✗ Failed {email}: {e}")

    print(f"\n  📨 Email summary: {sent} sent, {failed} failed")


def main():
    print("\n📧 Weekly Email Sender")
    print("=" * 40)

    subscribers = load_subscribers()
    if not subscribers:
        print("  No subscribers — nothing to send")
        return

    week_data, macro = load_current_week()
    if not week_data:
        print("  No week data found — nothing to send")
        return

    print(f"  📅 Week {week_data['week']}: {week_data.get('startDate')} → {week_data.get('endDate')}")
    print(f"  📊 {len(week_data.get('picks', []))} picks, status: {week_data.get('status')}")

    subject, html = build_email_html(week_data, macro)
    print(f"  📝 Subject: {subject}")

    send_emails(subscribers, subject, html)


if __name__ == '__main__':
    main()
