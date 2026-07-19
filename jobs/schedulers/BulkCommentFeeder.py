import asyncio
import json

from sqlalchemy import and_, func, or_

from database.CacheDatabase import cache_database
from database.Database import db_dependencies
from models.sql import Models


async def BulkCommentFeeder(db: db_dependencies):
    while True:
        try:
            event_data = await cache_database.rpoplpush("comment_queue", "comment_queue_processing")

            if not event_data:
                await asyncio.sleep(5)
                continue

            event = json.loads(event_data)
            post_id = event["post_id"]
            user_id = event["user_id"]
            comment = event["comment"]
            is_replay = event["is_replay"]

            cache_data_key = f"feed_post_{post_id}_comments"

            cached_data = await cache_database.get(cache_data_key)

            if cached_data:
                await cache_database.delete(cache_data_key)

            post = db.query(Models.OrganizationUpdates).filter(Models.OrganizationUpdates.id == post_id).first()
            if post:

                db.add(
                    Models.FeedComments(
                        user_id=user_id,
                        organization_update_id=post_id,
                        is_replay=is_replay,
                        comment=comment,
                    )
                )

                db.commit()

                await cache_database.lrem("comment_queue_processing", 1, event_data)
                await cache_database.expire(f"user:{user_id}:comment_on_post", 600)
                await cache_database.expire(f"post:{post_id}:comment", 600)

        except Exception as e:
            await asyncio.sleep(5)
           
