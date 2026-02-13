import email
import logging
import socket
import ssl
import smtplib
import re
from email.header import decode_header
from email.message import Message
from email.mime.text import MIMEText
from typing import List, Optional

logger = logging.getLogger(__name__)


class IMAPClient:
    """简化的 IMAP 客户端"""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock = None

    def _recv_until_tag(self, tag: str, timeout: float = 15.0) -> str:
        import time
        start = time.time()
        data = b''

        while time.time() - start < timeout:
            try:
                self.sock.settimeout(timeout - (time.time() - start))
                chunk = self.sock.recv(8192)
                if not chunk:
                    break
                data += chunk
                if tag.encode() in data:
                    break
            except socket.timeout:
                break

        return data.decode('latin-1', errors='ignore')

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=30)
        self.sock = ssl._create_unverified_context().wrap_socket(self.sock, server_hostname=self.host)
        self.sock.recv(4096)

    def login(self, username: str, password: str):
        tag = "LOG1"
        self.sock.sendall(f"{tag} LOGIN {username} {password}\r\n".encode())
        resp = self._recv_until_tag(tag)
        if 'OK' not in resp:
            raise Exception(f"Login failed: {resp}")

    def send_id(self, username: str):
        tag = "ID01"
        cmd = f'ID ("name" "SupportMail" "version" "1.0" "vendor" "Support" "support-email" "{username}")'
        self.sock.sendall(f"{tag} {cmd}\r\n".encode())
        resp = self._recv_until_tag(tag)
        logger.info(f"IMAP ID: {resp[:100]}")

    def select_inbox(self) -> int:
        tag = "SELE"
        self.sock.sendall(f"{tag} SELECT INBOX\r\n".encode())
        resp = self._recv_until_tag(tag)
        match = re.search(r'\* (\d+) EXISTS', resp)
        return int(match.group(1)) if match else 0

    def search_all(self) -> List[str]:
        """搜索所有邮件"""
        tag = "SEA1"
        self.sock.sendall(f"{tag} SEARCH ALL\r\n".encode())
        resp = self._recv_until_tag(tag)
        match = re.search(r'\* SEARCH (.+?)\r?\n', resp)
        if match:
            ids = match.group(1).strip().split()
            if ids:
                return ids
        return []

    def search_unseen(self) -> List[str]:
        """搜索未读邮件"""
        tag = "SEA2"
        self.sock.sendall(f"{tag} SEARCH UNSEEN\r\n".encode())
        resp = self._recv_until_tag(tag)
        match = re.search(r'\* SEARCH (.+?)\r?\n', resp)
        if match:
            ids = match.group(1).strip().split()
            if ids:
                return ids
        return []

    def fetch_email(self, email_id: str) -> Optional[Message]:
        tag = "FET1"
        self.sock.sendall(f"{tag} FETCH {email_id} RFC822\r\n".encode())
        resp = self._recv_until_tag(tag)

        # 网易格式: * N FETCH (RFC822 {size}\r\n<content>\r\n)
        # 或标准格式: * N FETCH (RFC822 {size})\r\n<content>
        # 尝试多种匹配模式

        # 模式1: 网易格式 (RFC822 {size}
        match = re.search(r'\* \d+ FETCH \(RFC822 (\d+)\}\r?\n', resp)
        if match:
            size = int(match.group(1))
            # 找到邮件内容开始位置
            content_start = match.end()
            content = resp[content_start:content_start + size]
            try:
                return email.message_from_bytes(content.encode('latin-1'))
            except:
                pass

        # 模式2: 尝试直接查找 {size}
        match = re.search(r'RFC822 \{(\d+)\}\r?\n', resp)
        if match:
            size = int(match.group(1))
            content_start = match.end()
            content = resp[content_start:content_start + size]
            try:
                return email.message_from_bytes(content.encode('latin-1'))
            except:
                pass

        # 模式3: 找到 FETCH ( 之后的内容
        match = re.search(r'FETCH \(.*?\{(\d+)\}\r?\n', resp, re.DOTALL)
        if match:
            size = int(match.group(1))
            content_start = match.end()
            content = resp[content_start:content_start + size]
            try:
                return email.message_from_bytes(content.encode('latin-1'))
            except:
                pass

        return None

    def close(self):
        if self.sock:
            try:
                self.sock.sendall(b"LOG1 LOGOUT\r\n")
                self.sock.recv(1024)
            except:
                pass
            self.sock.close()


def _decode_subject(subject: str) -> str:
    decoded_parts = decode_header(subject)
    return ''.join(p.decode(e or 'utf-8', errors='ignore') if isinstance(p, bytes) else p for p, e in decoded_parts)


def _decode_sender(sender: str) -> str:
    """Decode sender field, handling encoded names and email addresses"""
    if not sender:
        return ""
    decoded_parts = decode_header(sender)
    parts = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            parts.append(part.decode(encoding or 'utf-8', errors='ignore'))
        else:
            parts.append(part)
    return ''.join(parts)


def _extract_body(msg: Message) -> tuple[str, str]:
    text_parts, html_parts = [], []
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain" and not part.get("Content-Disposition"):
                text_parts.append((part.get_payload(decode=True) or b"").decode(part.get_content_charset() or 'utf-8', errors='ignore'))
            elif ct == "text/html" and not part.get("Content-Disposition"):
                html_parts.append((part.get_payload(decode=True) or b"").decode(part.get_content_charset() or 'utf-8', errors='ignore'))
    else:
        text_parts.append((msg.get_payload(decode=True) or b"").decode(msg.get_content_charset() or 'utf-8', errors='ignore'))
    return '\n'.join(text_parts).strip(), '\n'.join(html_parts).strip()


def _parse_date(date_str: str) -> str:
    """Parse RFC 2822 date string to ISO 8601 format"""
    from datetime import datetime
    import email.utils
    
    if not date_str:
        return datetime.utcnow().isoformat()
    
    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        return dt.isoformat()
    except Exception:
        # Fallback to current time if parsing fails
        return datetime.utcnow().isoformat()


def fetch_unreplied(host: str, port: int, username: str, password: str, use_ssl: bool = True) -> list[dict]:
    mail = IMAPClient(host, port)

    try:
        mail.connect()
        mail.login(username, password)
        mail.send_id(username)
        mail.select_inbox()
    except Exception as e:
        logger.error(f"IMAP failed: {e}")
        mail.close()
        raise ValueError(f"IMAP failed: {e}")

    # 先尝试搜索未读邮件
    email_ids = mail.search_unseen()
    search_type = "UNSEEN"

    # 如果没有未读邮件,搜索所有邮件
    if not email_ids:
        logger.info("No unseen emails found, searching all emails...")
        email_ids = mail.search_all()
        search_type = "ALL"

    if not email_ids:
        mail.close()
        return []

    emails = []
    for eid in email_ids:
        msg = mail.fetch_email(eid)
        if msg:
            emails.append({
                "message_id": msg.get("Message-ID"),
                "sender": _decode_sender(msg.get("From", "")),
                "subject": _decode_subject(msg.get("Subject", "")),
                "received_at": _parse_date(msg.get("Date")),
                "body_text": _extract_body(msg)[0],
                "body_html": _extract_body(msg)[1],
            })
            logger.info(f"Got email: {emails[-1]['subject'][:50]}")

    mail.close()
    logger.info(f"Fetched {len(emails)} emails (search: {search_type})")
    return emails


def send_reply(host: str, port: int, username: str, password: str, to_addr: str, subject: str, body: str, use_ssl: bool = True) -> Optional[str]:
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = username
    msg["To"] = to_addr

    server = smtplib.SMTP_SSL(host, port) if use_ssl else smtplib.SMTP(host, port)
    if not use_ssl:
        server.starttls()

    try:
        server.login(username, password)
        server.sendmail(username, [to_addr], msg.as_string())
    finally:
        server.quit()
    return "OK"
