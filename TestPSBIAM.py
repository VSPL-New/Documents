import boto3
import psycopg2
import os
 
def connect_with_iam():
    # Set your AWS credentials (via environment variables, IAM role, or AWS credentials file)
    # Generate authentication token
    rds_client = boto3.client('rds', region_name='eu-west-2')
    try:
        token = rds_client.generate_db_auth_token(
            DBHostname='pstestdb.c98ugik06bfe.eu-west-2.rds.amazonaws.com',
            Port=5432,
            DBUsername='psadmin_iam',
            Region='eu-west-2'
        )
        print(f"Token generated successfully, length: {len(token)}")
        print(f"Token starts with: {token[:50]}...")
        # Connect to database
        connection = psycopg2.connect(
            host='pstestdb.c98ugik06bfe.eu-west-2.rds.amazonaws.com',
            port=5432,
            database='postgres',  # Try with 'postgres' database first
            user='psadmin_iam',
            password=token,
            sslmode='require',
            connect_timeout=10
        )
        cursor = connection.cursor()
        cursor.execute("SELECT current_user, current_database();")
        result = cursor.fetchone()
        print(f"Connected as: {result[0]} to database: {result[1]}")
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
 
if __name__ == "__main__":
    connect_with_iam()

    # I'm Apurvika!!