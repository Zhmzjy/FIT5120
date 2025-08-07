#!/bin/bash

echo "=== Melbourne Parking System 数据库设置脚本 ==="
echo ""

# 检查PostgreSQL是否安装
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL未安装，请先安装PostgreSQL"
    echo "在macOS上可以使用: brew install postgresql"
    exit 1
fi

# 检查PostgreSQL服务是否运行
if ! pgrep -x "postgres" > /dev/null; then
    echo "⚠️  PostgreSQL服务未运行，正在启动..."
    if command -v brew &> /dev/null; then
        brew services start postgresql
    else
        sudo service postgresql start
    fi
    sleep 3
fi

# 数据库配置 - 使用当前系统用户
DB_NAME="parking_system"
DB_USER=$(whoami)

echo "🔄 创建数据库..."
# 创建数据库（如果不存在）
createdb $DB_NAME 2>/dev/null || echo "数据库可能已存在"

echo "🔄 执行数据库schema..."
# 执行schema创建
psql -d $DB_NAME -f database/complete_schema.sql

echo "✅ 数据库设置完成！"
echo ""
echo "现在你可以运行以下命令："
echo "1. 导入数据: python3 database/import_data.py"
echo "2. 启动Flask应用: python3 backend/app.py"
echo ""
