import uuid
from apps.directorates.models import Directorate

class DirectorateSlugConverter:
    regex = '[\\w-]+'

    def to_python(self, value):
        # Try as UUID first
        try:
            return uuid.UUID(value)
        except ValueError:
            # Not a UUID, try as slug
            # We match slugs by normalizing the names of directorates
            import unicodedata
            import re
            
            def get_slug(name):
                v = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('ascii')
                v = re.sub(r'[^\w\s-]', '', v).strip().lower()
                return re.sub(r'[-\s]+', '-', v)

            for d in Directorate.objects.all():
                if get_slug(d.name) == value:
                    return d.pk
            
            return value # Fallback to string if not found, though views might fail later

    def to_url(self, value):
        # If we have a Directorate object, return its slug
        if isinstance(value, Directorate):
            return value.slug
        
        # If we have a UUID, try to get the directorate slug
        if isinstance(value, (uuid.UUID, str)):
            try:
                d = Directorate.objects.filter(pk=value).first()
                if d:
                    return d.slug
            except (ValueError, TypeError):
                pass
        
        return str(value)
