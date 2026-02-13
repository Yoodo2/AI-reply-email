import re
from typing import Dict, Optional
from datetime import datetime


def extract_customer_name(sender: str) -> str:
    """从发件人邮箱或名称中提取客户名字"""
    if not sender:
        return "Valued Customer"
    
    # 尝试提取名称部分 (Name <email@example.com>)
    name_match = re.match(r'^([^<]+)', sender)
    if name_match:
        name = name_match.group(1).strip()
        # 如果名称包含空格，取第一个单词作为名字
        if ' ' in name:
            return name.split()[0]
        return name
    
    # 尝试从邮箱提取 (john.doe@example.com -> John)
    email_match = re.match(r'^([^@.]+)', sender)
    if email_match:
        local_part = email_match.group(1)
        # 处理点号分隔 (john.doe -> John)
        if '.' in local_part:
            return local_part.split('.')[0].capitalize()
        return local_part.capitalize()
    
    return "Valued Customer"


def extract_order_number(text: str) -> str:
    """从邮件内容中提取订单号"""
    if not text:
        return "[Order Number]"
    
    # 常见的订单号格式
    patterns = [
        r'[Oo]rder\s*#?\s*[:#]?\s*([A-Z0-9-]{4,20})',
        r'[Oo]rder\s+[Nn]umber\s*[:#]?\s*([A-Z0-9-]{4,20})',
        r'[Oo]rder\s*ID\s*[:#]?\s*([A-Z0-9-]{4,20})',
        r'#\s*([A-Z0-9-]{6,20})',
        r'订单\s*[:#]?\s*([A-Z0-9-]{4,20})',
        r'[Pp]urchase\s*#?\s*[:#]?\s*([A-Z0-9-]{4,20})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return "[Order Number]"


def extract_product_name(text: str) -> str:
    """从邮件内容中提取产品名称"""
    if not text:
        return "[Product Name]"
    
    # 尝试匹配常见的产品描述模式
    patterns = [
        r'[Pp]roduct\s*[:#]?\s*["\']?([^"\'\n]{3,50})["\']?',
        r'[Ii]tem\s*[:#]?\s*["\']?([^"\'\n]{3,50})["\']?',
        r'[Bb]ought\s+["\']?([^"\'\n]{3,50})["\']?',
        r'[Pp]urchased\s+["\']?([^"\'\n]{3,50})["\']?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    
    return "[Product Name]"


def extract_refund_amount(text: str) -> str:
    """从邮件内容中提取退款金额"""
    if not text:
        return "[Refund Amount]"
    
    # 匹配货币格式
    patterns = [
        r'\$\s*([\d,]+\.?\d*)',
        r'€\s*([\d,]+\.?\d*)',
        r'£\s*([\d,]+\.?\d*)',
        r'([\d,]+\.?\d*)\s*dollars?',
        r'([\d,]+\.?\d*)\s*USD',
        r'金额\s*[:#]?\s*¥?\s*([\d,]+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = match.group(1).replace(',', '')
            # 确定货币符号
            if '$' in match.group(0) or 'USD' in match.group(0).upper() or 'dollar' in match.group(0).lower():
                return f"${amount}"
            elif '€' in match.group(0):
                return f"€{amount}"
            elif '£' in match.group(0):
                return f"£{amount}"
            elif '¥' in match.group(0) or '金额' in match.group(0):
                return f"¥{amount}"
            return f"${amount}"
    
    return "[Refund Amount]"


def extract_tracking_number(text: str) -> str:
    """从邮件内容中提取物流追踪号"""
    if not text:
        return "[Tracking Number]"
    
    # 常见物流追踪号格式
    patterns = [
        r'[Tt]racking\s*#?\s*[:#]?\s*([A-Z0-9]{10,25})',
        r'[Tt]racking\s+[Nn]umber\s*[:#]?\s*([A-Z0-9]{10,25})',
        r'[Tt]rack\s*#?\s*[:#]?\s*([A-Z0-9]{10,25})',
        r'物流单号\s*[:#]?\s*([A-Z0-9]{10,25})',
        r'快递单号\s*[:#]?\s*([A-Z0-9]{10,25})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return "[Tracking Number]"


def extract_carrier_name(text: str) -> str:
    """从邮件内容中提取物流商名称"""
    if not text:
        return "[Carrier]"
    
    # 常见物流商
    carriers = [
        'UPS', 'FedEx', 'DHL', 'USPS', 'EMS', 'SF Express', 
        '顺丰', '中通', '圆通', '申通', '韵达', '菜鸟',
        'Amazon Logistics', 'OnTrac', 'LaserShip'
    ]
    
    text_upper = text.upper()
    for carrier in carriers:
        if carrier.upper() in text_upper:
            return carrier
    
    return "[Carrier]"


def build_variables(
    email_row: Dict,
    template_variables: Optional[str] = None,
    company_name: str = "Our Company",
    company_email: str = "support@example.com",
    company_phone: str = "+1 (800) 123-4567"
) -> Dict[str, str]:
    """
    根据邮件内容构建模板变量字典
    """
    email_text = f"{email_row.get('subject', '')} {email_row.get('body_text', '')}"
    sender = email_row.get('sender', '')
    
    # 基础变量
    variables = {
        # 客户信息
        "Customer Name": extract_customer_name(sender),
        "Customer Email": sender if '@' in sender else "[Customer Email]",
        
        # 订单信息
        "Order Number": extract_order_number(email_text),
        "Product Name": extract_product_name(email_text),
        "Refund Amount": extract_refund_amount(email_text),
        
        # 物流信息
        "Tracking Number": extract_tracking_number(email_text),
        "Carrier Name": extract_carrier_name(email_text),
        "Tracking URL": f"[Tracking URL - https://track.example.com/{extract_tracking_number(email_text)}]",
        "Shipping Status": "In Transit",
        "Estimated Date": "[Estimated Delivery Date]",
        
        # 订单状态
        "Order Status": "Processing",
        "Order Date": datetime.now().strftime("%B %d, %Y"),
        "Last Update": datetime.now().strftime("%B %d, %Y"),
        "Next Steps Description": "We are preparing your order for shipment. You will receive a tracking number once it ships.",
        
        # 公司信息
        "Company Name": company_name,
        "Company Email": company_email,
        "Phone Number": company_phone,
        
        # 其他常用变量
        "Inquiry Topic": "your inquiry",
        "FAQ URL": "https://example.com/faq",
        "Size Guide URL": "https://example.com/size-guide",
        "Return Policy URL": "https://example.com/returns",
    }
    
    # 如果模板有特定变量定义，确保这些变量都有值
    if template_variables:
        var_list = [v.strip() for v in template_variables.split(',') if v.strip()]
        for var in var_list:
            if var not in variables:
                variables[var] = f"[{var}]"
    
    return variables


def render_template(template: str, variables: Dict[str, str]) -> str:
    """
    渲染模板，替换所有变量占位符
    """
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{key}}}", str(value))
    
    # 检查是否还有未替换的变量
    remaining = re.findall(r'\{([^}]+)\}', result)
    for var in remaining:
        result = result.replace(f"{{{var}}}", f"[{var}]")
    
    return result
