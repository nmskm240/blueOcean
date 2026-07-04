from typing import Any

from redis import Redis

from blueOcean.settings import COUNTER_KEY_PREFIX


class RedisCounterRepository:
    def __init__(self, redis_url: str) -> None:
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.index_key = f"{COUNTER_KEY_PREFIX}:ids"

    def ping(self) -> bool:
        return self.redis.ping()

    def key(self, counter_id: str) -> str:
        return f"{COUNTER_KEY_PREFIX}:{counter_id}"

    def create(self, counter_id: str) -> None:
        pipeline = self.redis.pipeline()
        pipeline.sadd(self.index_key, counter_id)
        pipeline.hset(
            self.key(counter_id),
            mapping={
                "id": counter_id,
                "count": 0,
                "status": "starting",
                "pid": "",
                "stop_requested": 0,
            },
        )
        pipeline.execute()

    def prepare_start(self, counter_id: str) -> bool:
        key = self.key(counter_id)
        result = self.redis.eval(
            """
            if redis.call('EXISTS', KEYS[1]) == 0 then return 0 end
            local status = redis.call('HGET', KEYS[1], 'status')
            if status == 'starting' or status == 'running' then return 0 end
            redis.call('HSET', KEYS[1],
                'count', 0, 'status', 'starting', 'stop_requested', 0)
            return 1
            """,
            1,
            key,
        )
        return result == 1

    def mark_running(self, counter_id: str, pid: int) -> None:
        self.redis.hset(
            self.key(counter_id), mapping={"status": "running", "pid": pid}
        )

    def increment(self, counter_id: str) -> int:
        return self.redis.hincrby(self.key(counter_id), "count", 1)

    def request_stop(self, counter_id: str) -> None:
        if self.redis.exists(self.key(counter_id)):
            self.redis.hset(
                self.key(counter_id),
                mapping={"status": "stopping", "stop_requested": 1},
            )

    def should_stop(self, counter_id: str) -> bool:
        key = self.key(counter_id)
        return not self.redis.exists(key) or self.redis.hget(key, "stop_requested") == "1"

    def mark_stopped(self, counter_id: str) -> None:
        if self.redis.exists(self.key(counter_id)):
            self.redis.hset(
                self.key(counter_id),
                mapping={"status": "stopped", "stop_requested": 0},
            )

    def delete(self, counter_id: str) -> None:
        pipeline = self.redis.pipeline()
        pipeline.srem(self.index_key, counter_id)
        pipeline.delete(self.key(counter_id))
        pipeline.execute()

    def list(self) -> list[dict[str, Any]]:
        counter_ids = sorted(self.redis.smembers(self.index_key))
        pipeline = self.redis.pipeline()
        for counter_id in counter_ids:
            pipeline.hgetall(self.key(counter_id))
        records = pipeline.execute()
        return [
            {
                "id": record["id"],
                "count": int(record.get("count", 0)),
                "is_alive": record.get("status") in {"starting", "running"},
                "status": record.get("status", "stopped"),
                "pid": int(record["pid"]) if record.get("pid") else None,
            }
            for record in records
            if record
        ]
