"""
数据库初始化脚本

执行 init_db.sql 来创建数据库和表结构
"""
import pymysql
import sys
from pathlib import Path

# 数据库连接配置
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3308,
    'user': 'root',
    'password': '123456',
    'charset': 'utf8mb4'
}

def init_database():
    """初始化数据库"""
    try:
        # 读取 SQL 脚本
        sql_file = Path(__file__).parent / 'init_db.sql'
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # 连接数据库
        print("正在连接到 MySQL...")
        connection = pymysql.connect(**DB_CONFIG)
        
        try:
            with connection.cursor() as cursor:
                # 分割并执行 SQL 语句
                statements = [s.strip() for s in sql_script.split(';') if s.strip()]
                
                for statement in statements:
                    # 跳过注释和空语句
                    if statement.startswith('--') or statement.startswith('/*'):
                        continue
                    
                    try:
                        cursor.execute(statement)
                        print(f"✓ 执行成功")
                    except Exception as e:
                        print(f"✗ 执行失败: {statement[:50]}...")
                        print(f"  错误: {e}")
                
                connection.commit()
                print("\n✓ 数据库初始化完成！")
                
        finally:
            connection.close()
            
    except FileNotFoundError:
        print(f"✗ 错误: 找不到 SQL 文件 {sql_file}")
        sys.exit(1)
    except pymysql.Error as e:
        print(f"✗ 数据库错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 未知错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    init_database()
