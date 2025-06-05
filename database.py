import mysql.connector
from datetime import datetime
from config import DB_CONFIG

class DatabaseManager:
    """数据库管理类"""
    
    @staticmethod
    def get_connection():
        return mysql.connector.connect(**DB_CONFIG)
    
    @staticmethod
    def execute_query(query, params=None, fetch_one=False, fetch_all=False):
        conn = None
        cursor = None
        try:
            conn = DatabaseManager.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

def init_database():
    """初始化数据库表结构"""
    create_tables_sql = """
    -- 用户表
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR(36) PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role ENUM('user', 'admin') DEFAULT 'user',
        balance DECIMAL(10,2) DEFAULT 0.00,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- 充电桩表
    CREATE TABLE IF NOT EXISTS charging_piles (
        id VARCHAR(20) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        status ENUM('available', 'occupied', 'fault', 'maintenance') DEFAULT 'available',
        power_rating DECIMAL(5,2) NOT NULL DEFAULT 7.00,
        location VARCHAR(200),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    );
    
    -- 充电记录表
    CREATE TABLE IF NOT EXISTS charging_records (
        id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL,
        pile_id VARCHAR(20) NOT NULL,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP,
        power_consumed DECIMAL(8,3) DEFAULT 0.000,
        electricity_fee DECIMAL(10,2) DEFAULT 0.00,
        service_fee DECIMAL(10,2) DEFAULT 0.00,
        total_fee DECIMAL(10,2) DEFAULT 0.00,
        status ENUM('charging', 'completed', 'cancelled', 'fault') DEFAULT 'charging',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (pile_id) REFERENCES charging_piles(id),
        INDEX idx_user_created (user_id, created_at),
        INDEX idx_pile_created (pile_id, created_at)
    );
    
    -- 系统日志表
    CREATE TABLE IF NOT EXISTS system_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        level ENUM('DEBUG', 'INFO', 'WARNING', 'ERROR') NOT NULL,
        message TEXT NOT NULL,
        user_id VARCHAR(36),
        ip_address VARCHAR(45),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_level_created (level, created_at),
        INDEX idx_user_created (user_id, created_at)
    );
    """
    
    try:
        # 分割SQL语句并执行
        statements = [stmt.strip() for stmt in create_tables_sql.split(';') if stmt.strip()]
        for statement in statements:
            if statement:
                DatabaseManager.execute_query(statement)
        print("数据库表初始化完成")
    except Exception as e:
        print(f"数据库表初始化失败: {e}")

    pass