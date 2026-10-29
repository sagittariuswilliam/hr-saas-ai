"""
数据库初始化脚本
创建默认管理员账号
运行方式: python init_db.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.core.security import get_password_hash
from app.models.models import User, UserRole
from sqlalchemy.orm import Session

print("🚀 开始初始化数据库...")

# 创建所有表
Base.metadata.create_all(bind=engine)
print("✅ 数据库表创建完成")

# 创建默认管理员
db: Session = next(get_db())

# 检查管理员是否已存在
admin = db.query(User).filter(User.username == "admin").first()
if admin:
    print("⚠️  管理员账号已存在，跳过创建")
else:
    admin = User(
        username="admin",
        real_name="系统管理员",
        email="admin@hr-saas.com",
        phone="13800138000",
        role=UserRole.ADMIN,
        password_hash=get_password_hash("admin123"),
        status=1
    )
    db.add(admin)
    db.commit()
    print("✅ 默认管理员账号创建完成")
    print("   用户名: admin")
    print("   密码:   admin123")

print()
print("🎉 数据库初始化完成！")