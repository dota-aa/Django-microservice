from celery import shared_task


@shared_task
def add_nums(a, b):
    return a + b
