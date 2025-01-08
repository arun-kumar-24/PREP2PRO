import redis # type: ignore

# Replace 'internal-redis-url' and 'port' with actual details
redis_client = redis.StrictRedis(
    host='redis://red-ctv3fpogph6c73eqsmfg:6379',
    port=6379,  # Default Redis port
    db=0,       # Default database
    decode_responses=True  # To get string responses instead of bytes
)

# import redis # type: ignore
# from dotenv import load_dotenv # type: ignore
# import os

# # Load environment variables
# load_dotenv()

# # Set up the Redis client
# REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
# REDIS_PORT = os.getenv('REDIS_PORT', 6379)
# REDIS_DB = os.getenv('REDIS_DB', 0)

# # Create the Redis client
# redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)