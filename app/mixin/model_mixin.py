class ModelMixin:
    def get_model(self):
        context = self.get_context()
        return context.get('model')

    def get_fields(self):
        model = self.get_model()
        meta = getattr(model, '_meta')
        return meta.fields_map
