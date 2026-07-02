class TvTemplateMixin:
    tv_template_name = None

    def get_template_names(self):
        if self.request.GET.get("tv") == "1" and self.tv_template_name:
            return [self.tv_template_name]
        return super().get_template_names()
