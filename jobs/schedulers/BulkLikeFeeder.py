import asyncio
import json

from sqlalchemy import and_, func, or_

from database.CacheDatabase import cache_database
from database.Database import db_dependencies
from models.sql import Models


async def BulkLikeFeeder(db: db_dependencies):
    while True:
        try:
            event_data = await cache_database.rpoplpush("likes_queue", "likes_queue_processing")

            if not event_data:
                await asyncio.sleep(5)
                continue

            event = json.loads(event_data)
            post_id = event["post_id"]
            user_id = event["user_id"]
            action = event["action"]

            cache_data_key = f"feed_post_{post_id}_likes"

            cached_data = await cache_database.get(cache_data_key)

            if cached_data:
                await cache_database.delete(cache_data_key)

            post = db.query(Models.OrganizationUpdates).filter(Models.OrganizationUpdates.id == post_id).first()
            if post:
                existing_like = (
                    db.query(Models.FeedLikes)
                    .filter(
                        and_(
                            Models.FeedLikes.organization_update_id == post_id,
                            Models.FeedLikes.user_id == user_id,
                        )
                    )
                    .first()
                )
                if action == "like":
                    if not existing_like:
                        db.add(Models.FeedLikes(user_id=user_id, organization_update_id=post_id))
                elif action == "unlike":

                    if existing_like:
                        db.delete(existing_like)
                    else:
                        print(f"No existing like found for user {user_id} on post {post_id}.")

                db.commit()

                await cache_database.lrem("likes_queue_processing", 1, event_data)

                await cache_database.expire(f"user:{user_id}:liked_posts", 600)
                await cache_database.expire(f"post:{post_id}:likes", 600)

        except Exception as e:
            # print(e)
            await asyncio.sleep(5)
