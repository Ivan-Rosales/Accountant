from functools import cached_property


class ModelMixin:
    _model = None

    @cached_property
    def model(self):
        if self._model is None:
            context = self.get_context()
            self._model = context.get('model')
        return self._model

    @cached_property
    def fields(self):
        return self.model.__table__.columns
