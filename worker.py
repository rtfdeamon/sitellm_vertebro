from apps.worker.main import celery_app, voice_train_model

if __name__ == "__main__":
    celery_app.start()
