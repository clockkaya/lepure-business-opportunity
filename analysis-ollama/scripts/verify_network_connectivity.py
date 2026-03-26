#!/usr/bin/env python3
"""
网络连通性验证脚本
用于验证 analysis-ollama 容器的网络连接是否正常
"""

import socket
import sys
import pymysql
import requests
from typing import Dict, List, Tuple


def test_dns_resolution(hostname: str) -> Tuple[bool, str]:
    """测试 DNS 解析"""
    try:
        ip = socket.gethostbyname(hostname)
        return True, f"✓ DNS 解析成功: {hostname} -> {ip}"
    except socket.gaierror as e:
        return False, f"✗ DNS 解析失败: {hostname} - {e}"


def test_http_connectivity(url: str, timeout: int = 5) -> Tuple[bool, str]:
    """测试 HTTP 连接"""
    try:
        response = requests.get(url, timeout=timeout)
        return True, f"✓ HTTP 连接成功: {url} (状态码: {response.status_code})"
    except requests.exceptions.RequestException as e:
        return False, f"✗ HTTP 连接失败: {url} - {e}"


def test_mysql_connectivity(host: str, port: int, user: str, password: str) -> Tuple[bool, str]:
    """测试 MySQL 连接"""
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            connect_timeout=5
        )
        server_info = conn.get_server_info()
        conn.close()
        return True, f"✓ MySQL 连接成功: {host}:{port} (版本: {server_info})"
    except pymysql.Error as e:
        return False, f"✗ MySQL 连接失败: {host}:{port} - {e}"


def main():
    """主函数"""
    print("=" * 60)
    print("Analysis-Ollama 容器网络连通性验证")
    print("=" * 60)
    print()

    results: List[Tuple[str, bool, str]] = []

    # 1. DNS 解析测试
    print("1. DNS 解析测试")
    print("-" * 60)
    for hostname in ['app', 'db', 'wewe-rss', 'opportunity-mysql']:
        success, message = test_dns_resolution(hostname)
        results.append((f"DNS: {hostname}", success, message))
        print(message)
    print()

    # 2. HTTP 连接测试
    print("2. HTTP 连接测试")
    print("-" * 60)
    
    # WeWe-RSS (使用 app 主机名)
    success, message = test_http_connectivity('http://app:4000/api/feeds')
    results.append(("HTTP: WeWe-RSS (app)", success, message))
    print(message)
    
    # WeWe-RSS (使用 wewe-rss 主机名)
    success, message = test_http_connectivity('http://wewe-rss:4000/api/feeds')
    results.append(("HTTP: WeWe-RSS (wewe-rss)", success, message))
    print(message)
    
    # Ollama 外部服务器
    success, message = test_http_connectivity('http://192.168.10.43:11434/api/tags')
    results.append(("HTTP: Ollama", success, message))
    print(message)
    print()

    # 3. MySQL 连接测试
    print("3. MySQL 连接测试")
    print("-" * 60)
    
    # 使用 db 主机名
    success, message = test_mysql_connectivity(
        host='db',
        port=3306,
        user='root',
        password='3kmmFUNQQepDHP4uHpNz'
    )
    results.append(("MySQL: db", success, message))
    print(message)
    
    # 使用 opportunity-mysql 主机名
    success, message = test_mysql_connectivity(
        host='opportunity-mysql',
        port=3306,
        user='root',
        password='3kmmFUNQQepDHP4uHpNz'
    )
    results.append(("MySQL: opportunity-mysql", success, message))
    print(message)
    print()

    # 4. 总结
    print("=" * 60)
    print("验证总结")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for _, success, _ in results if success)
    failed = total - passed
    
    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print()
    
    if failed > 0:
        print("失败的测试:")
        for name, success, message in results:
            if not success:
                print(f"  - {name}: {message}")
        print()
        sys.exit(1)
    else:
        print("✓ 所有网络连通性测试通过！")
        sys.exit(0)


if __name__ == '__main__':
    main()
