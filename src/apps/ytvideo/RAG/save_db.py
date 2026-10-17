from apps.ytvideo.models import YtVideo,YtVideoChunks


def save_db(chunks:list[dict],meta_data:dict,yt_video_id):
    YtVideo.objects.get(youtube_id= yt_video_id)