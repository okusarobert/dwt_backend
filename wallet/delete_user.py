#!/usr/bin/env python3
import psycopg2
import sys

def delete_user(email):
    """Delete a user and all related data from the database"""
    try:
        # Connect to database
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='tondeka',
            user='tondeka',
            password='tondeka'
        )
        cur = conn.cursor()

        # Find the user
        cur.execute('SELECT id, email, first_name, last_name FROM users WHERE email = %s', (email,))
        user = cur.fetchone()
        
        if user:
            user_id = user[0]
            print(f'Found user: ID={user_id}, Email={user[1]}, Name={user[2]} {user[3]}')
            
            # Delete related records first (to avoid foreign key constraints)
            cur.execute('DELETE FROM accounts WHERE user_id = %s', (user_id,))
            accounts_deleted = cur.rowcount
            print(f'Deleted {accounts_deleted} accounts')
            
            cur.execute('DELETE FROM email_verify WHERE user_id = %s', (user_id,))
            email_verify_deleted = cur.rowcount
            print(f'Deleted {email_verify_deleted} email verification records')
            
            # Check for other related tables and delete if they exist
            tables_to_check = [
                'forgot_password',
                'transactions', 
                'trades',
                'portfolio_balances',
                'crypto_addresses'
            ]
            
            for table in tables_to_check:
                try:
                    cur.execute(f'DELETE FROM {table} WHERE user_id = %s', (user_id,))
                    deleted = cur.rowcount
                    if deleted > 0:
                        print(f'Deleted {deleted} records from {table}')
                except psycopg2.Error as e:
                    # Table might not exist, continue
                    pass
            
            # Delete the user
            cur.execute('DELETE FROM users WHERE id = %s', (user_id,))
            users_deleted = cur.rowcount
            print(f'Deleted {users_deleted} user record')
            
            conn.commit()
            print('✅ User and all related data deleted successfully')
            return True
        else:
            print('❌ User not found')
            return False

    except psycopg2.Error as e:
        print(f'❌ Database error: {e}')
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f'❌ Error: {e}')
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    email = sys.argv[1] if len(sys.argv) > 1 else 'okusarobert@gmail.com'
    delete_user(email)
