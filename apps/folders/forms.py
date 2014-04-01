from __future__ import absolute_import
from .models import Folder
from .permissions import PERMISSION_FOLDER_VIEW
from acls.models import AccessEntry
from django import forms
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
from folders.literals import DEFAULT_CSV_FILENAME
from permissions.models import Permission
import logging

logger = logging.getLogger(__name__)

class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ('title',)

class FolderListForm(forms.Form):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        logger.debug('user: %s' % user)
        super(FolderListForm, self).__init__(*args, **kwargs)

        queryset = Folder.objects.all()
        try:
            Permission.objects.check_permissions(user, [PERMISSION_FOLDER_VIEW])
        except PermissionDenied:
            queryset = AccessEntry.objects.filter_objects_by_access(PERMISSION_FOLDER_VIEW, user, queryset)

        self.fields['folder'] = forms.ModelChoiceField(
            queryset=queryset,
            label=_(u'Folder'))

class FolderExportMetadataForm(forms.Form):
    
    csv_filename = forms.CharField(initial=DEFAULT_CSV_FILENAME, label=_(u'CSV filename'), required=False, help_text=_(u'The filename of the csv file that will contain the documents names and corresponding metadata.'))
    
    def __init__(self, *args, **kwargs):
        super( FolderExportMetadataForm, self).__init__(*args, **kwargs)