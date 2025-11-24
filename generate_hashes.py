"""Generate fresh bcrypt hashes"""
import bcrypt

# Generate hashes
admin_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt(rounds=12))
user_hash = bcrypt.hashpw(b"user123", bcrypt.gensalt(rounds=12))

print("Fresh bcrypt hashes:")
print("=" * 50)
print(f"ADMIN_PASSWORD_HASH = {admin_hash}")
print(f"USER_PASSWORD_HASH = {user_hash}")

# Verify they work
print("\nVerification:")
print(f"Admin: {'✅' if bcrypt.checkpw(b'admin123', admin_hash) else '❌'}")
print(f"User: {'✅' if bcrypt.checkpw(b'user123', user_hash) else '❌'}")
