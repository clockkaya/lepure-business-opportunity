"""
数据库验证脚本

检查数据库中的记录和统计信息
"""
from sqlalchemy import create_engine, text
import sys
import os

# 添加父目录到路径以便导入配置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.settings import settings

def check_database():
    """检查数据库记录"""
    try:
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            # 检查 analysis_articles 表
            result = conn.execute(text("SELECT COUNT(*) FROM analysis_articles"))
            article_count = result.scalar()
            print(f"\n📊 Analysis Articles 表记录数: {article_count}")
            
            result = conn.execute(text("SELECT COUNT(*) FROM analysis_articles WHERE status='processed'"))
            processed_count = result.scalar()
            print(f"   - 已处理: {processed_count}")
            
            result = conn.execute(text("SELECT COUNT(*) FROM analysis_articles WHERE status='pending'"))
            pending_count = result.scalar()
            print(f"   - 待处理: {pending_count}")
            
            result = conn.execute(text("SELECT COUNT(*) FROM analysis_articles WHERE status='error'"))
            error_count = result.scalar()
            print(f"   - 错误: {error_count}")
            
            # 检查 analysis_extracted_projects 表
            result = conn.execute(text("SELECT COUNT(*) FROM analysis_extracted_projects"))
            project_count = result.scalar()
            print(f"\n📊 Analysis Extracted Projects 表记录数: {project_count}")
            
            # 显示最近的几条记录
            if processed_count > 0:
                print(f"\n📝 最近处理的文章:")
                result = conn.execute(text("""
                    SELECT a.title, a.status, p.company_name, p.project_name, p.project_stage
                    FROM analysis_articles a
                    LEFT JOIN analysis_extracted_projects p ON a.id = p.article_id
                    WHERE a.status = 'processed'
                    ORDER BY a.fetched_at DESC
                    LIMIT 5
                """))
                
                for row in result:
                    title, status, company, project, stage = row
                    print(f"   - {title[:50]}...")
                    print(f"     公司: {company}, 项目: {project}, 阶段: {stage}")
            
            print(f"\n✓ 数据库检查完成")
            
    except Exception as e:
        print(f"\n✗ 数据库检查失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check_database()
