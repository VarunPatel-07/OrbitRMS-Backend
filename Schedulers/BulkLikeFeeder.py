import asyncio
import json

from sqlalchemy import and_, func, or_

from Database.CacheDatabase import cache_database
from Database.Database import db_dependencies
from SqlModels import Models


async def BulkLikeFeeder(db: db_dependencies):
    try:
        event_data = await cache_database.lpop("likes_queue")
        if event_data:
            print(event_data)
            event = json.loads(event_data)
            post_id = event["post_id"]
            user_id = event["user_id"]
            action = event["action"]

            post = (
                db.query(Models.OrganizationUpdates)
                .filter(Models.OrganizationUpdates.id == post_id)
                .first()
            )
            if post:
                if action == "like":
                    db.add(Models.FeedLikes(user_id=user_id, organization_update_id=post_id))
                elif action == "unlike":

                    like = (
                        db.query(Models.FeedLikes)
                        .filter(
                            and_(
                                Models.FeedLikes.organization_update_id == post_id,
                                Models.FeedLikes.user_id == user_id,
                            )
                        )
                        .first()
                    )

                    db.delete(like)

                db.commit()
        else:
            await asyncio.sleep(5)  # Prevent busy looping

    except Exception as e:
        print(e)
