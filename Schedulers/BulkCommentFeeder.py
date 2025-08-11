import asyncio
import json

from sqlalchemy import and_, func, or_

from Database.CacheDatabase import cache_database
from Database.Database import db_dependencies
from SqlModels import Models


async def BulkCommentFeeder(db: db_dependencies):
    try:
        event_data = await cache_database.lpop("comment_queue")
        if event_data:
            print(event_data)
            event = json.loads(event_data)
            post_id = event["post_id"]
            user_id = event["user_id"]
            comment = event["comment"]
            is_replay = event["is_replay"]

            post = (
                db.query(Models.OrganizationUpdates)
                .filter(Models.OrganizationUpdates.id == post_id)
                .first()
            )
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
        else:
            await asyncio.sleep(5)  # Prevent busy looping

    except Exception as e:
        print(e)
