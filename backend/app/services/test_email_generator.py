"""
测试邮件生成器
用于生成模拟真实用户场景的测试邮件
"""
import random
import uuid
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径（支持直接运行此文件）
backend_path = Path(__file__).resolve().parents[2]
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

try:
    from app.db import db
    from app.services.email_client import send_reply
except ImportError:
    # 如果添加路径后仍然导入失败，使用相对导入
    pass

# 随机姓名库
FIRST_NAMES = [
    "张", "李", "王", "刘", "陈", "杨", "赵", "黄", "周", "吴",
    "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗",
    "John", "Jane", "Michael", "Sarah", "David", "Emily", "Chris", "Lisa", "Tom", "Amy"
]

LAST_NAMES = [
    "伟", "芳", "娜", "敏", "静", "丽", "强", "磊", "军", "洋",
    "勇", "艳", "杰", "涛", "明", "超", "秀英", "华", "鑫", "宇",
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"
]

# 产品名称库
PRODUCTS = [
    "Wireless Bluetooth Headphones",
    "Smart Watch Series 5",
    "Laptop Stand Adjustable",
    "USB-C Hub 7-in-1",
    "Mechanical Keyboard RGB",
    "Gaming Mouse Pro",
    "Portable Power Bank 20000mAh",
    "4K Webcam HD",
    "Noise Cancelling Earbuds",
    "Phone Case Premium",
    "Yoga Mat Non-Slip",
    "Water Bottle Insulated",
    "Backpack Travel",
    "Sunglasses Polarized",
    "Watch Band Leather"
]

# 快递公司库
CARRIERS = [
    ("UPS", "1Z999AA10123456784"),
    ("FedEx", "789456123012345678"),
    ("DHL", "1234567890"),
    ("USPS", "9400111899223456789012"),
    ("EMS", "EA123456789CN"),
    ("SF Express", "SF1234567890"),
    ("顺丰", "SF1234567890"),
    ("中通", "7011234567890"),
    ("圆通", "YT1234567890"),
    ("韵达", "YD1234567890"),
]

# 订单状态描述
ORDER_STATUSES = [
    "processing",
    "shipped",
    "out for delivery",
    "delivered",
    "pending payment"
]


def generate_random_name() -> str:
    """生成随机姓名（中英文）"""
    if random.random() > 0.3:  # 70% 中文名
        return random.choice(FIRST_NAMES) + random.choice(LAST_NAMES[:10])
    else:
        return f"{random.choice(FIRST_NAMES[20:])} {random.choice(LAST_NAMES[20:])}"


def generate_order_number() -> str:
    """生成随机订单号"""
    prefix = random.choice(["ORD", "ORD", "ORD", "PO", "SO"])
    timestamp = datetime.now().strftime("%Y%m%d")
    random_num = ''.join(random.choices('0123456789', k=8))
    return f"{prefix}-{timestamp}-{random_num}"


def generate_tracking_number() -> tuple[str, str]:
    """生成随机物流追踪号和快递公司"""
    carrier, tracking = random.choice(CARRIERS)
    # 添加一些随机变化
    if random.random() > 0.5:
        tracking = tracking[:-4] + ''.join(random.choices('0123456789', k=4))
    return carrier, tracking


def generate_product_name() -> str:
    """生成随机产品名称"""
    return random.choice(PRODUCTS)


def generate_order_date() -> str:
    """生成随机订单日期（过去30天内）"""
    days_ago = random.randint(1, 30)
    order_date = datetime.now() - timedelta(days=days_ago)
    return order_date.strftime("%B %d, %Y")


def generate_amount() -> str:
    """生成随机金额"""
    amount = round(random.uniform(19.99, 499.99), 2)
    return f"${amount:.2f}"


# 邮件模板
EMAIL_TEMPLATES = {
    "shipping": {
        "subject": "Order Status Inquiry - {order_number}",
        "templates": [
            # 英文催发货
            """Hi Customer Service,

I placed an order ({order_number}) on {order_date} for {product_name}, but I haven't received any shipping updates yet. Could you please check the status and let me know when it will be shipped?

Thank you,
{customer_name}""",

            # 中文催发货
            """您好，

我于 {order_date} 订购了订单号 {order_number} 的商品 {product_name}，但至今未收到发货通知。请问什么时候可以发货？

谢谢！
{customer_name}""",
        ]
    },
    "refund": {
        "subject": "Refund Request - Order {order_number}",
        "templates": [
            # 英文退款（商品问题）
            """Hello,

I recently purchased {product_name} (Order: {order_number}) on {order_date}, but unfortunately the item arrived damaged. I would like to request a full refund of {amount}.

Please advise on how to proceed with the return.

Best regards,
{customer_name}""",

            # 中文退款（取消订单）
            """您好，

我想取消订单号 {order_number} 的订单（{order_date} 购买的 {product_name}），并申请全额退款 {amount}。

订单尚未发货，请尽快处理。

谢谢！
{customer_name}""",
        ]
    },
    "delivery": {
        "subject": "Package Not Received - Order {order_number}",
        "templates": [
            # 英文未收到快递
            """Hi Support,

My package (Order: {order_number}) was shipped via {carrier} with tracking number {tracking_number} on {order_date}, but I still haven't received it. The tracking shows it should have been delivered {days_ago} days ago.

Could you please investigate this issue?

Thanks,
{customer_name}""",

            # 中文未收到快递
            """您好，

我于 {order_date} 通过 {carrier} 快递公司订购了订单号 {order_number} 的商品，快递单号是 {tracking_number}。物流信息显示已于 {days_ago} 天前送达，但我至今未收到包裹。

请帮忙核实处理，非常感谢！

{customer_name}""",
        ]
    }
}


def generate_email_content(email_type: str) -> dict:
    """
    生成指定类型的邮件内容（仅英文）

    Args:
        email_type: 邮件类型 ("shipping", "refund", "delivery")

    Returns:
        包含 subject 和 body 的字典
    """
    if email_type not in EMAIL_TEMPLATES:
        raise ValueError(f"Unknown email type: {email_type}")

    template_config = EMAIL_TEMPLATES[email_type]

    # 生成随机数据
    customer_name = generate_random_name()
    order_number = generate_order_number()
    order_date = generate_order_date()
    product_name = generate_product_name()
    amount = generate_amount()
    carrier, tracking_number = generate_tracking_number()
    days_ago = random.randint(3, 15)

    # 只选择英文模板（索引为偶数的模板：0, 2, 4...）
    english_templates = [tpl for i, tpl in enumerate(template_config["templates"]) if i % 2 == 0]
    template = random.choice(english_templates)

    # 替换变量
    body = template.format(
        customer_name=customer_name,
        order_number=order_number,
        order_date=order_date,
        product_name=product_name,
        amount=amount,
        carrier=carrier,
        tracking_number=tracking_number,
        days_ago=days_ago
    )

    # 替换主题中的变量
    subject = template_config["subject"].format(order_number=order_number)

    return {
        "subject": subject,
        "body": body,
        "sender_name": customer_name,
        "type": email_type,
        "order_number": order_number,
        "product_name": product_name
    }


def generateTestEmails(
    target_email: str,
    count: int = 3,
    email_types: Optional[list[str]] = None,
    smtp_config: Optional[dict] = None
) -> dict:
    """
    生成并发送测试邮件到指定邮箱

    Args:
        target_email: 目标邮箱地址
        count: 发送邮件数量
        email_types: 指定邮件类型列表，默认随机 ["shipping", "refund", "delivery"]
        smtp_config: SMTP 配置（可选，默认从数据库读取）

    Returns:
        发送结果统计
    """
    if email_types is None:
        email_types = ["shipping", "refund", "delivery"]

    # 获取 SMTP 配置
    if smtp_config is None:
        account = db.fetch_one("SELECT * FROM mail_accounts ORDER BY updated_at DESC LIMIT 1")
        if not account:
            return {"success": False, "error": "Mail account not configured"}
        smtp_config = {
            "host": account["smtp_host"],
            "port": account["smtp_port"],
            "username": account["username"],
            "password": account["password"],
            "use_ssl": bool(account["use_ssl"])
        }

    # 验证目标邮箱（安全限制）
    allowed_email = "yo17765767816@163.com"
    if target_email.lower() != allowed_email.lower():
        return {"success": False, "error": f"Only {allowed_email} is allowed for testing"}

    results = []
    success_count = 0

    for i in range(count):
        # 随机选择邮件类型
        email_type = random.choice(email_types)

        try:
            # 生成邮件内容
            email_content = generate_email_content(email_type)

            # 发送邮件
            response = send_reply(
                host=smtp_config["host"],
                port=smtp_config["port"],
                username=smtp_config["username"],
                password=smtp_config["password"],
                to_addr=target_email,
                subject=email_content["subject"],
                body=email_content["body"],
                use_ssl=smtp_config["use_ssl"]
            )

            results.append({
                "index": i + 1,
                "type": email_type,
                "subject": email_content["subject"],
                "sender": email_content["sender_name"],
                "order_number": email_content["order_number"],
                "status": "sent" if response == "OK" else "failed"
            })

            if response == "OK":
                success_count += 1

            # 添加小延迟避免过快发送
            import time
            time.sleep(0.5)

        except Exception as e:
            results.append({
                "index": i + 1,
                "type": email_type,
                "status": "error",
                "error": str(e)
            })

    return {
        "success": success_count > 0,
        "total": count,
        "sent": success_count,
        "failed": count - success_count,
        "results": results
    }


# 可独立运行的测试
if __name__ == "__main__":
    # 测试发送邮件
    print("Sending test emails to yo17765767816@163.com...")

    # 确保先初始化数据库
    from app.db.db import init_db
    init_db()

    result = generateTestEmails(
        target_email="yo17765767816@163.com",
        count=3
    )

    print(f"\nResult: {result}")
