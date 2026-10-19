from celery import shared_task
from .hierarchical_pipline import get_hierarchical_pipeline


@shared_task(bind=True,ingnore_result=True)
def coding_challange_create(youtube_id:str):
    hierarchical_pipeline_result = get_hierarchical_pipeline().invoke(
        {
            "youtube_id":youtube_id
        }
    )

    concepts = hierarchical_pipeline_result['concepts']
    


