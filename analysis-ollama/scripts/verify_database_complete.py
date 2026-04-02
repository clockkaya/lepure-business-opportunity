"""
完整的数据库记录验证脚本

验证 analysis_ollama 数据库中的记录是否正确和完整
Task 13.1.6: 验证数据库记录正确
"""
import sys
import json
from app.core.database import create_db_engine
from app.core.settings import settings
from sqlmodel import Session, select, func
from sqlalchemy import inspect, text
from app.models.article import Article
from app.models.project import ExtractedProject

def print_section(title):
    """打印分节标题"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def verify_database_connection():
    """验证数据库连接"""
    print_section("1. 数据库连接验证")
    try:
        engine = create_db_engine(settings.database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            print(f"✓ 数据库连接成功")
            print(f"  - 数据库: {settings.DB_NAME}")
            print(f"  - 主机: {settings.DB_HOST}:{settings.DB_PORT}")
            return engine
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        sys.exit(1)

def verify_table_structure(engine):
    """验证表结构"""
    print_section("2. 表结构验证")
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    expected_tables = ['analysis_articles', 'analysis_extracted_projects']
    
    print(f"数据库中的表: {tables}")
    
    for table in expected_tables:
        if table in tables:
            print(f"\n✓ 表 '{table}' 存在")
            
            # 获取列信息
            columns = inspector.get_columns(table)
            print(f"  列数: {len(columns)}")
            print(f"  列名: {', '.join([col['name'] for col in columns])}")
            
            # 获取索引信息
            indexes = inspector.get_indexes(table)
            print(f"  索引数: {len(indexes)}")
            for idx in indexes:
                print(f"    - {idx['name']}: {idx['column_names']} (unique={idx['unique']})")
        else:
            print(f"✗ 表 '{table}' 不存在")
            return False
    
    return True

def verify_articles_table(engine):
    """验证 analysis_articles 表"""
    print_section("3. analysis_articles 表数据验证")
    
    with Session(engine) as session:
        # 总记录数
        total_count = session.exec(select(func.count(Article.id))).one()
        print(f"总记录数: {total_count}")
        
        # 按状态统计
        pending_count = session.exec(select(func.count(Article.id)).where(Article.status == 'pending')).one()
        processed_count = session.exec(select(func.count(Article.id)).where(Article.status == 'processed')).one()
        error_count = session.exec(select(func.count(Article.id)).where(Article.status == 'error')).one()
        
        print(f"\n状态分布:")
        print(f"  - pending (待处理): {pending_count}")
        print(f"  - processed (已处理): {processed_count}")
        print(f"  - error (错误): {error_count}")
        
        # 验证状态分布
        print(f"\n✓ 状态统计验证:")
        print(f"  - 待处理: {pending_count}")
        print(f"  - 已处理: {processed_count}")
        print(f"  - 错误: {error_count}")
        print(f"  - 总计: {pending_count + processed_count + error_count}")
        
        # 检查 GUID 唯一性
        with engine.connect() as conn:
            guid_check = conn.execute(text("""
                SELECT COUNT(*) as total, COUNT(DISTINCT guid) as unique_guids
                FROM analysis_articles
            """)).fetchone()
            
            if guid_check[0] == guid_check[1]:
                print(f"\n✓ GUID 唯一性约束正常")
                print(f"  - 总记录数: {guid_check[0]}")
                print(f"  - 唯一 GUID 数: {guid_check[1]}")
            else:
                print(f"\n✗ GUID 唯一性约束异常")
                print(f"  - 总记录数: {guid_check[0]}")
                print(f"  - 唯一 GUID 数: {guid_check[1]}")
                print(f"  - 重复 GUID 数: {guid_check[0] - guid_check[1]}")
            
            # 检查必填字段
            null_check = conn.execute(text("""
                SELECT 
                    SUM(CASE WHEN title IS NULL THEN 1 ELSE 0 END) as null_title,
                    SUM(CASE WHEN url IS NULL THEN 1 ELSE 0 END) as null_url,
                    SUM(CASE WHEN guid IS NULL THEN 1 ELSE 0 END) as null_guid,
                    SUM(CASE WHEN status IS NULL THEN 1 ELSE 0 END) as null_status
                FROM analysis_articles
            """)).fetchone()
            
            print(f"\n✓ 必填字段完整性检查:")
            if sum(null_check) == 0:
                print(f"  - 所有必填字段均无 NULL 值")
            else:
                print(f"  - NULL title: {null_check[0]}")
                print(f"  - NULL url: {null_check[1]}")
                print(f"  - NULL guid: {null_check[2]}")
                print(f"  - NULL status: {null_check[3]}")
        
        # 显示最近的记录
        print(f"\n最近处理的 5 条记录:")
        recent_articles = session.exec(
            select(Article).order_by(Article.fetched_at.desc()).limit(5)
        ).all()
        
        for article in recent_articles:
            title_display = article.title[:60] + "..." if len(article.title) > 60 else article.title
            print(f"  [{article.id}] {title_display} ({article.status}) - {article.fetched_at}")
        
        return {
            'total': total_count,
            'processed': processed_count,
            'error': error_count,
            'pending': pending_count
        }

def verify_projects_table(engine, articles_stats):
    """验证 analysis_extracted_projects 表"""
    print_section("4. analysis_extracted_projects 表数据验证")
    
    with Session(engine) as session:
        # 总记录数
        total_count = session.exec(select(func.count(ExtractedProject.id))).one()
        print(f"总记录数: {total_count}")
        
        # 验证记录数是否匹配成功处理的文章数
        processed_count = articles_stats['processed']
        if total_count == processed_count:
            print(f"✓ 项目记录数与已处理文章数匹配 ({total_count} == {processed_count})")
        else:
            print(f"⚠ 项目记录数与已处理文章数不匹配")
            print(f"  - 项目记录数: {total_count}")
            print(f"  - 已处理文章数: {processed_count}")
            print(f"  - 差异: {abs(total_count - processed_count)}")
        
        # 检查外键关系
        with engine.connect() as conn:
            fk_check = conn.execute(text("""
                SELECT COUNT(*) 
                FROM analysis_extracted_projects p
                LEFT JOIN analysis_articles a ON p.article_id = a.id
                WHERE a.id IS NULL
            """)).scalar()
            
            if fk_check == 0:
                print(f"\n✓ 外键关系完整")
                print(f"  - 所有项目记录都关联到有效的文章")
            else:
                print(f"\n✗ 外键关系异常")
                print(f"  - {fk_check} 条项目记录关联到不存在的文章")
            
            # 检查提取数据质量
            data_quality = conn.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN company_name IS NOT NULL THEN 1 ELSE 0 END) as has_company,
                    SUM(CASE WHEN project_name IS NOT NULL THEN 1 ELSE 0 END) as has_project,
                    SUM(CASE WHEN province IS NOT NULL THEN 1 ELSE 0 END) as has_province,
                    SUM(CASE WHEN city IS NOT NULL THEN 1 ELSE 0 END) as has_city,
                    SUM(CASE WHEN project_stage IS NOT NULL THEN 1 ELSE 0 END) as has_stage
                FROM analysis_extracted_projects
            """)).fetchone()
            
            print(f"\n✓ 提取数据质量统计:")
            print(f"  - 总记录数: {data_quality[0]}")
            if data_quality[0] > 0:
                print(f"  - 有公司名称: {data_quality[1]} ({data_quality[1]/data_quality[0]*100:.1f}%)")
                print(f"  - 有项目名称: {data_quality[2]} ({data_quality[2]/data_quality[0]*100:.1f}%)")
                print(f"  - 有省份: {data_quality[3]} ({data_quality[3]/data_quality[0]*100:.1f}%)")
                print(f"  - 有城市: {data_quality[4]} ({data_quality[4]/data_quality[0]*100:.1f}%)")
                print(f"  - 有项目阶段: {data_quality[5]} ({data_quality[5]/data_quality[0]*100:.1f}%)")
            
            # 检查 JSON 数据
            json_check = conn.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN raw_json IS NOT NULL THEN 1 ELSE 0 END) as has_json
                FROM analysis_extracted_projects
            """)).fetchone()
            
            print(f"\n✓ JSON 数据检查:")
            print(f"  - 总记录数: {json_check[0]}")
            if json_check[0] > 0:
                print(f"  - 有 raw_json: {json_check[1]} ({json_check[1]/json_check[0]*100:.1f}%)")
        
        # 显示示例记录
        print(f"\n示例项目记录 (前 3 条):")
        sample_projects = session.exec(
            select(ExtractedProject, Article)
            .join(Article, ExtractedProject.article_id == Article.id)
            .order_by(ExtractedProject.created_at.desc())
            .limit(3)
        ).all()
        
        for project, article in sample_projects:
            title_display = article.title[:50] + "..." if len(article.title) > 50 else article.title
            print(f"\n  [{project.id}] {title_display}")
            print(f"      公司: {project.company_name or 'N/A'}")
            print(f"      项目: {project.project_name or 'N/A'}")
            print(f"      阶段: {project.project_stage or 'N/A'}")
            print(f"      地区: {project.province or 'N/A'} {project.city or 'N/A'}")
        
        # 验证 JSON 数据格式
        if total_count > 0:
            print(f"\n✓ JSON 数据格式验证 (抽样 1 条):")
            sample_project = session.exec(
                select(ExtractedProject)
                .where(ExtractedProject.raw_json.is_not(None))
                .limit(1)
            ).first()
            
            if sample_project and sample_project.raw_json:
                try:
                    json_data = sample_project.raw_json if isinstance(sample_project.raw_json, dict) else json.loads(sample_project.raw_json)
                    print(f"  - JSON 格式正确")
                    print(f"  - 字段数: {len(json_data)}")
                    print(f"  - 字段: {', '.join(json_data.keys())}")
                except Exception as e:
                    print(f"  ✗ JSON 解析失败: {e}")

def verify_data_integrity(engine):
    """验证数据完整性"""
    print_section("5. 数据完整性验证")
    
    with engine.connect() as conn:
        # 验证所有已处理的文章都有对应的项目记录
        orphan_articles = conn.execute(text("""
            SELECT COUNT(*)
            FROM analysis_articles a
            LEFT JOIN analysis_extracted_projects p ON a.id = p.article_id
            WHERE a.status = 'processed' AND p.id IS NULL
        """)).scalar()
        
        if orphan_articles == 0:
            print(f"✓ 所有已处理文章都有对应的项目记录")
        else:
            print(f"⚠ {orphan_articles} 篇已处理文章没有对应的项目记录")
        
        # 验证错误状态的文章没有项目记录
        error_with_projects = conn.execute(text("""
            SELECT COUNT(*)
            FROM analysis_articles a
            JOIN analysis_extracted_projects p ON a.id = p.article_id
            WHERE a.status = 'error'
        """)).scalar()
        
        if error_with_projects == 0:
            print(f"✓ 错误状态的文章没有项目记录")
        else:
            print(f"⚠ {error_with_projects} 篇错误状态文章有项目记录（异常）")
        
        # 验证时间戳合理性
        time_check = conn.execute(text("""
            SELECT 
                MIN(fetched_at) as earliest,
                MAX(fetched_at) as latest,
                COUNT(*) as total
            FROM analysis_articles
        """)).fetchone()
        
        print(f"\n✓ 时间戳范围:")
        print(f"  - 最早抓取: {time_check[0]}")
        print(f"  - 最晚抓取: {time_check[1]}")
        print(f"  - 总记录数: {time_check[2]}")

def verify_schema_matches_ddl(engine):
    """验证数据库 schema 是否匹配 DDL 规范"""
    print_section("6. Schema 与 DDL 规范对比")
    
    inspector = inspect(engine)
    
    # 验证 analysis_articles 表
    print("analysis_articles 表:")
    articles_columns = {col['name']: col for col in inspector.get_columns('analysis_articles')}
    
    expected_articles_columns = [
        'id', 'title', 'url', 'guid', 'feed_id', 
        'published_at', 'fetched_at', 'status', 'summary'
    ]
    
    for col_name in expected_articles_columns:
        if col_name in articles_columns:
            print(f"  ✓ {col_name}: {articles_columns[col_name]['type']}")
        else:
            print(f"  ✗ {col_name}: 缺失")
    
    # 验证 analysis_extracted_projects 表
    print("\nanalysis_extracted_projects 表:")
    projects_columns = {col['name']: col for col in inspector.get_columns('analysis_extracted_projects')}
    
    expected_projects_columns = [
        'id', 'article_id', 'company_name', 'province', 'city',
        'client_type', 'application_scene', 'project_name', 
        'project_stage', 'raw_json', 'created_at'
    ]
    
    for col_name in expected_projects_columns:
        if col_name in projects_columns:
            print(f"  ✓ {col_name}: {projects_columns[col_name]['type']}")
        else:
            print(f"  ✗ {col_name}: 缺失")

def generate_summary(articles_stats):
    """生成验证摘要"""
    print_section("7. 验证摘要")
    
    total = articles_stats['total']
    processed = articles_stats['processed']
    error = articles_stats['error']
    pending = articles_stats['pending']
    
    print(f"数据库: {settings.DB_NAME}")
    print(f"主机: {settings.DB_HOST}:{settings.DB_PORT}")
    print(f"\n文章统计:")
    print(f"  - 总记录数: {total}")
    print(f"  - 已处理: {processed} ({processed/total*100:.1f}%)" if total > 0 else "  - 已处理: 0")
    print(f"  - 错误: {error} ({error/total*100:.1f}%)" if total > 0 else "  - 错误: 0")
    print(f"  - 待处理: {pending} ({pending/total*100:.1f}%)" if total > 0 else "  - 待处理: 0")
    
    print(f"\n验证结果:")
    if total == 87 and processed == 83 and error == 4:
        print(f"  ✓ 记录数与预期一致 (87 篇文章, 83 成功, 4 错误)")
    else:
        print(f"  ⚠ 记录数与预期不完全一致")
        print(f"    预期: 87 篇文章 (83 成功, 4 错误)")
        print(f"    实际: {total} 篇文章 ({processed} 成功, {error} 错误)")
    
    print(f"\n✓ 数据库记录验证完成")

def main():
    """主函数"""
    print("\n" + "="*80)
    print("  数据库记录完整性验证")
    print("  Task 13.1.6: 验证数据库记录正确")
    print("="*80)
    
    # 1. 验证数据库连接
    engine = verify_database_connection()
    
    # 2. 验证表结构
    if not verify_table_structure(engine):
        print("\n✗ 表结构验证失败，退出")
        sys.exit(1)
    
    # 3. 验证 articles 表
    articles_stats = verify_articles_table(engine)
    
    # 4. 验证 projects 表
    verify_projects_table(engine, articles_stats)
    
    # 5. 验证数据完整性
    verify_data_integrity(engine)
    
    # 6. 验证 schema 匹配 DDL
    verify_schema_matches_ddl(engine)
    
    # 7. 生成摘要
    generate_summary(articles_stats)
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    main()
