# DynamoDB User Storage Setup

Your user management system now uses **DynamoDB** for persistent storage! 🎉

## What Changed

### 1. **User Storage**

- ✅ **Before**: Users stored in memory (lost on restart)
- ✅ **Now**: Users stored in DynamoDB (persistent across restarts)

### 2. **Dual Mode Operation**

#### Local Development (Current)

```bash
# Set in your environment
export LOCAL_MODE=true
# or in Windows PowerShell
$env:LOCAL_MODE="true"
```

- Uses in-memory storage (same as before)
- No AWS credentials needed
- Perfect for local testing

#### Production/AWS (Cloud)

```bash
export LOCAL_MODE=false  # or just don't set it
export AWS_REGION=us-east-1
export USERS_TABLE=UsersTable
```

- Uses real DynamoDB
- Persistent across restarts
- Shared across multiple backend instances

## Files Modified

### `bs/src/jwt_auth.py`

- Added DynamoDB client setup
- Created helper functions: `_get_user_from_db()`, `_put_user_to_db()`, `_delete_user_from_db()`, `_scan_all_users()`
- Auto-initializes default admin/user in DynamoDB on startup
- Handles both bytes and string password hashes (DynamoDB compatibility)

### `template.yaml` (AWS SAM)

- Added `UsersTable` DynamoDB table resource
- Added `ArtifactsTable` DynamoDB table resource (for future use)
- Configured Lambda permissions for DynamoDB access
- Set environment variables: `USERS_TABLE`, `ARTIFACTS_TABLE`

### `requirements.txt`

- Added `boto3>=1.28.0` (AWS SDK)
- Added `botocore>=1.31.0` (boto3 dependency)

## Local Testing (No Changes Needed!)

Your backend still works locally without any AWS setup:

```bash
# Start backend normally
python -m uvicorn bs.src.app:app --reload --host 0.0.0.0 --port 8000
```

It automatically uses in-memory storage when `LOCAL_MODE=true` (or not set).

## AWS Deployment

### Option 1: Quick Deploy (AWS SAM)

```bash
# Install dependencies
pip install -r requirements.txt

# Build and deploy
sam build
sam deploy --guided
```

This will:

1. Create DynamoDB `UsersTable`
2. Create DynamoDB `ArtifactsTable`
3. Deploy Lambda function with proper permissions
4. Initialize default admin/user accounts

### Option 2: Manual DynamoDB Setup

If you want to create the table manually:

```bash
aws dynamodb create-table \
    --table-name UsersTable \
    --attribute-definitions AttributeName=username,AttributeType=S \
    --key-schema AttributeName=username,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

Then set environment variables:

```bash
export LOCAL_MODE=false
export AWS_REGION=us-east-1
export USERS_TABLE=UsersTable
```

## DynamoDB Table Schema

### UsersTable

```
Partition Key: username (String)

Attributes:
- username: string (primary key)
- hashed_password: string (bcrypt hash)
- role: string ("admin" or "user")
- email: string
```

### Default Users

When deployed to AWS, these users are auto-created:

- **admin** / admin123 (role: admin)
- **user** / user123 (role: user)

## Benefits

### ✅ Persistence

- Users survive backend restarts
- No data loss

### ✅ Scalability

- Multiple backend instances share same user database
- No synchronization issues

### ✅ AWS Integration

- Serverless (pay per request)
- Auto-scaling
- Managed backups (with Point-in-Time Recovery)

### ✅ Development Friendly

- Local mode still works without AWS
- Easy to switch between local/cloud

## Monitoring

### Check Users in DynamoDB

```bash
# List all users
aws dynamodb scan --table-name UsersTable --region us-east-1

# Get specific user
aws dynamodb get-item \
    --table-name UsersTable \
    --key '{"username": {"S": "admin"}}' \
    --region us-east-1
```

## Cost Estimate

DynamoDB with on-demand pricing:

- **Free Tier**: 25 GB storage, 25 WCU, 25 RCU
- **Pay-per-request**: ~$1.25 per million writes, ~$0.25 per million reads
- **Estimated**: <$1/month for typical user management workload

## Troubleshooting

### "Table not found" error

```bash
# Check if table exists
aws dynamodb describe-table --table-name UsersTable --region us-east-1

# Create it manually (see Option 2 above)
```

### "Access Denied" error

Your Lambda needs DynamoDB permissions. Check `template.yaml` has:

```yaml
Policies:
  - DynamoDBCrudPolicy:
      TableName: !Ref UsersTable
```

### Local mode not working

Set environment variable:

```bash
# Linux/Mac
export LOCAL_MODE=true

# Windows PowerShell
$env:LOCAL_MODE="true"

# Windows CMD
set LOCAL_MODE=true
```

## Next Steps

1. **Test locally** - Everything still works as before
2. **Deploy to AWS** - Run `sam deploy` when ready
3. **Create users via UI** - Use the admin panel at `/users`
4. **Users persist** - They'll survive restarts! 🎉
