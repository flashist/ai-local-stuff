"""
Post text + media to a VK community wall.
"""
import vk_api
from vk_api.upload import VkUpload

import config
from fetcher import TelegramPost


def post_to_vk(post: TelegramPost, text: str) -> str:
    """Upload media and create a wall post. Returns the URL of the new post."""
    # Community token for wall posting
    community_session = vk_api.VkApi(token=config.VK_COMMUNITY_TOKEN)
    vk = community_session.get_api()

    # User token for video upload (video.save is unavailable with group auth)
    user_session = vk_api.VkApi(token=config.VK_USER_TOKEN)
    user_upload = VkUpload(user_session)

    attachments: list[str] = []

    videos = [p for p, t in zip(post.media_paths, post.media_types) if t == "video"]

    for video_path in videos[:1]:
        result = user_upload.video(
            video_path,
            group_id=abs(config.VK_OWNER_ID),
            is_private=0,
        )
        attachments.append(f"video{result['owner_id']}_{result['video_id']}")

    response = vk.wall.post(
        owner_id=config.VK_OWNER_ID,
        message=text,
        attachments=",".join(attachments),
        from_group=1,
    )

    post_id = response["post_id"]
    owner = abs(config.VK_OWNER_ID)
    return f"https://vk.com/wall-{owner}_{post_id}"
