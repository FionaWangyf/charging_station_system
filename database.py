import mysql.connector
from mysql.connector import pooling
import redis
from config import Config
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self):
        # MySQL连接池 - 增加连接池大小并添加配置
        self.mysql_pool = pooling.MySQLConnectionPool(
            pool_name="charging_pool",
            pool_size=30,
            pool_reset_session=True,
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE,
            charset='utf8mb4',
            autocommit=False,
            use_unicode=True,
            connection_timeout=30
        )
        
        # Redis连接
        self.redis_client = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            password=Config.REDIS_PASSWORD,
            decode_responses=True
        )
        
        self.init_database()
    
    def get_mysql_connection(self):
        """获取MySQL连接，添加更详细的错误处理"""
        try:
            connection = self.mysql_pool.get_connection()
            return connection
        except mysql.connector.errors.PoolError as e:
            print(f"连接池错误: {e}")
            print(f"当前连接池状态 - 池名: {self.mysql_pool.pool_name}, 大小: {self.mysql_pool.pool_size}")
            raise
        except Exception as e:
            print(f"获取数据库连接时发生未知错误: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """上下文管理器，确保连接总是被正确释放"""
        connection = None
        try:
            connection = self.get_mysql_connection()
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                try:
                    connection.close()
                except Exception as close_error:
                    print(f"关闭数据库连接时出错: {close_error}")
    
    @contextmanager
    def get_cursor(self, dictionary=True):
        """获取游标的上下文管理器"""
        with self.get_connection() as connection:
            cursor = None
            try:
                cursor = connection.cursor(dictionary=dictionary)
                yield cursor, connection
                connection.commit()
            except Exception as e:
                connection.rollback()
                raise
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except Exception as close_error:
                        print(f"关闭游标时出错: {close_error}")
    
    def get_redis_client(self):
        return self.redis_client
    
    def init_database(self):
        """初始化数据库表结构"""
        with self.get_cursor() as (cursor, connection):
            # 创建数据库表
            tables = {
                'users': """
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        email VARCHAR(100),
                        phone VARCHAR(20),
                        battery_capacity DECIMAL(10,2) DEFAULT 50.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """,
                'charging_piles': """
                    CREATE TABLE IF NOT EXISTS charging_piles (
                        id VARCHAR(30) PRIMARY KEY,
                        pile_type ENUM('fast', 'trickle') NOT NULL,
                        power DECIMAL(10,2) NOT NULL,
                        status ENUM('online', 'offline', 'maintenance', 'fault') DEFAULT 'online',
                        location_info TEXT,
                        install_date DATE,
                        total_charging_count INT DEFAULT 0,
                        total_charging_time DECIMAL(10,2) DEFAULT 0.0,
                        total_charging_amount DECIMAL(10,2) DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """,
                'charging_sessions': """
                    CREATE TABLE IF NOT EXISTS charging_sessions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        session_id VARCHAR(50) UNIQUE NOT NULL,
                        user_id INT NOT NULL,
                        pile_id VARCHAR(30) NULL,
                        queue_number VARCHAR(30),
                        charging_mode ENUM('fast', 'trickle') NOT NULL,
                        requested_amount DECIMAL(10,2) NOT NULL,
                        actual_amount DECIMAL(10,2) DEFAULT 0.0,
                        charging_duration DECIMAL(10,2) DEFAULT 0.0,
                        start_time TIMESTAMP NULL,
                        end_time TIMESTAMP NULL,
                        status Varchar(50),
                        charging_fee DECIMAL(10,2) DEFAULT 0.0,
                        service_fee DECIMAL(10,2) DEFAULT 0.0,
                        total_fee DECIMAL(10,2) DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (pile_id) REFERENCES charging_piles(id)
                    )
                """,
                'system_config': """
                    CREATE TABLE IF NOT EXISTS system_config (
                        config_key VARCHAR(100) PRIMARY KEY,
                        config_value TEXT NOT NULL,
                        description TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """
            }
            
            for table_name, create_sql in tables.items():
                cursor.execute(create_sql)
                print(f"表 {table_name} 创建完成")
            
            # 初始化充电桩数据
            self.init_charging_piles(cursor)
            
            # 初始化系统配置
            self.init_system_config(cursor)
        
        print("数据库初始化完成")
    
    def init_charging_piles(self, cursor):
        """初始化充电桩数据"""
        # 检查是否已有数据
        cursor.execute("SELECT COUNT(*) as cnt FROM charging_piles")
        count = cursor.fetchone()['cnt']
        if count == 0:
            # 插入快充桩
            fast_piles = [
                ('A', 'fast', Config.FAST_CHARGING_POWER, 'online', '快充区域A'),
                ('B', 'fast', Config.FAST_CHARGING_POWER, 'online', '快充区域B')
            ]
            
            # 插入慢充桩
            trickle_piles = [
                ('C', 'trickle', Config.TRICKLE_CHARGING_POWER, 'online', '慢充区域C'),
                ('D', 'trickle', Config.TRICKLE_CHARGING_POWER, 'online', '慢充区域D'),
                ('E', 'trickle', Config.TRICKLE_CHARGING_POWER, 'online', '慢充区域E')
            ]
            
            all_piles = fast_piles + trickle_piles
            
            for pile_data in all_piles:
                cursor.execute("""
                    INSERT INTO charging_piles (id, pile_type, power, status, location_info)
                    VALUES (%s, %s, %s, %s, %s)
                """, pile_data)
            
            print("充电桩初始化数据插入完成")
    
    def init_system_config(self, cursor):
        """初始化系统配置"""
        configs = [
            ('fast_charging_pile_num', str(Config.FAST_CHARGING_PILE_NUM), '快充桩数量'),
            ('trickle_charging_pile_num', str(Config.TRICKLE_CHARGING_PILE_NUM), '慢充桩数量'),
            ('waiting_area_size', str(Config.WAITING_AREA_SIZE), '等候区容量'),
            ('charging_queue_len', str(Config.CHARGING_QUEUE_LEN), '充电桩队列长度'),
            ('fast_charging_power', str(Config.FAST_CHARGING_POWER), '快充功率'),
            ('trickle_charging_power', str(Config.TRICKLE_CHARGING_POWER), '慢充功率'),
            ('peak_price', str(Config.PEAK_PRICE), '峰时电价'),
            ('normal_price', str(Config.NORMAL_PRICE), '平时电价'),
            ('valley_price', str(Config.VALLEY_PRICE), '谷时电价'),
            ('service_price', str(Config.SERVICE_PRICE), '服务费单价')
        ]
        
        for config in configs:
            cursor.execute("""
                INSERT INTO system_config (config_key, config_value, description)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE config_value = VALUES(config_value)
            """, config)
    
    def get_pool_status(self):
        """获取连接池状态信息"""
        try:
            return {
                'pool_name': self.mysql_pool.pool_name,
                'pool_size': self.mysql_pool.pool_size,
                'status': 'active'
            }
        except Exception as e:
            return {'error': str(e)}
    
    def check_pool_health(self):
        """检查连接池健康状态"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                return True
        except Exception as e:
            print(f"连接池健康检查失败: {e}")
            return False