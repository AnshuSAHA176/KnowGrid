from django_redis import get_redis_connection

redis_client = get_redis_connection('default')


MAX_PENDING_JOBS = 500
SLOT = "admission:video"
JOB_IDS = "admission:video:reserved"


RESERVATION_CHEACK_SCRIPT="""

local max_jobs = tonumber(ARGV[1])
if not max_jobs or max_jobs <= 0 then
    return "invalid_capacity"
end
local job_id = ARGV[2]

local slot = tonumber(redis.call("HGET",KEYS[1],"slot")) or 0

local job_exits = redis.call("SISMEMBER",KEYS[2],job_id)

if job_exits == 1 then
return "already_in_queue"
end

if slot>=max_jobs then 
return "capacity_full"
else 
slot = slot+1
redis.call("SADD",KEYS[2],job_id)
redis.call("HSET",KEYS[1],"slot",slot)

return "accepted"
end

"""


def check_slot(job_id:str):
    result = redis_client.eval(
        RESERVATION_CHEACK_SCRIPT,
        
        2,
        SLOT,
        JOB_IDS,
        MAX_PENDING_JOBS,
        job_id,

    )
    return result.decode() if isinstance(result,bytes) else result

RELEASE_RESERVATION_SCRIPT ="""

local job_id = ARGV[1]
local job_exists = redis.call("SISMEMBER",KEYS[1],job_id)

if job_exists == 0 then
return "job_id_not_in_queue"
end

local counter = tonumber(redis.call("HGET",KEYS[2],"slot")) or 0
if counter <=0 then 
return "counter_inconsistent"

end 

redis.call("SREM",KEYS[1],job_id)
counter=counter-1
redis.call("HSET",KEYS[2],"slot",counter)

return "job_removed"
"""


def release_slot(job_id:str):
    result = redis_client.eval(
        RELEASE_RESERVATION_SCRIPT,
        2,
        JOB_IDS,
        SLOT,
        job_id

    )
    return result.decode() if isinstance(result,bytes) else result