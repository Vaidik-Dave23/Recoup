from enum import Enum


class MerchantRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"


class MerchantStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class OrderStatus(str, Enum):
    CREATED = "created"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    CREATED = "created"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class CaseType(str, Enum):
    PAYMENT_FAILED = "payment_failed"
    ABANDONED_CHECKOUT = "abandoned_checkout"
    OVERDUE_INVOICE = "overdue_invoice"


class RecoveryStage(str, Enum):
    NEW = "new"
    TRIAGE = "triage"
    STRATEGIZE = "strategize"
    MESSAGING = "messaging"
    RETRY = "retry"
    RECOVERED = "recovered"
    ESCALATED = "escalated"


class RecoveryCaseStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    RECOVERED = "recovered"
    ESCALATED = "escalated"
    CLOSED = "closed"


class InvestigationNode(str, Enum):
    TRIAGE = "triage"
    STRATEGIZE = "strategize"
    GENERATE_CONTENT = "generate_content"
    EXECUTE = "execute"
    CHECK_OUTCOME = "check_outcome"
    ESCALATE = "escalate"


class ActionType(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    RETRY = "retry"


class ActionChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    RAZORPAY_RETRY = "razorpay_retry"


class ActionStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    SUCCEEDED = "succeeded"


class EscalationStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
