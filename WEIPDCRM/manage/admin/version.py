# coding:utf-8

"""
DCRM - Darwin Cydia Repository Manager
Copyright (C) 2017  WU Zheng <i.82@me.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import unicode_literals

import os

from django.contrib import admin
from django.forms import ModelForm
from django.utils.safestring import mark_safe

from django_rq import job
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.actions import delete_selected

from suit import apps
from suit_redactor.widgets import RedactorWidget

from WEIPDCRM.models.version import Version


class VersionForm(ModelForm):
    class Meta(object):
        widgets = {
            'update_logs': RedactorWidget,
            'c_description': RedactorWidget,
        }


@job("high")
def hash_update_job(queryset):
    succeed = True
    for e in queryset:
        try:
            e.update_hash()
            e.save()
        except Exception as e:
            succeed = False
    return {"success": succeed}


class VersionAdmin(admin.ModelAdmin):
    def make_enabled(self, request, queryset):
        """
        :type queryset: QuerySet
        """
        queryset.update(enabled=True)
    make_enabled.short_description = _("Mark selected versions as enabled")

    def make_disabled(self, request, queryset):
        """
        :type queryset: QuerySet
        """
        queryset.update(enabled=False)
    make_disabled.short_description = _("Mark selected versions as disabled")

    def batch_hash_update(self, request, queryset):
        """
        :type queryset: QuerySet
        """
        hash_update_job.delay(queryset)
        self.message_user(request, _("Hash updating job has been added to the \"high\" queue."))
    batch_hash_update.short_description = _("Update hashes of selected versions")

    def storage_(self, instance):
        """
        :type instance: Version
        """
        return mark_safe('<a href="' + instance.storage_link + '" target="_blank">' + instance.storage_link + '</a>')
    
    form = VersionForm
    actions = [make_enabled, make_disabled, batch_hash_update, delete_selected]
    filter_horizontal = (
        'os_compatibility',
        'device_compatibility'
    )
    list_display = (
        'enabled',
        'c_version',
        'c_package',
        'c_name',
        'c_section'
    )
    list_filter = ('enabled', 'c_section')
    list_display_links = ('c_version', )
    search_fields = ['c_version', 'c_package', 'c_name']
    readonly_fields = [
        'storage_',
        'download_times',
        'c_md5',
        'c_sha1',
        'c_sha256',
        'c_sha512',
        'c_size',
        'created_at'
    ]
    fieldsets = [
        # Common
        ('Basic', {
            'classes': ('suit-tab suit-tab-common',),
            'fields': ['enabled', 'c_package', 'c_version']
        }),
        ('Display', {
            'classes': ('suit-tab suit-tab-common',),
            'fields': ['c_name', 'c_section', 'c_icon', 'c_description', 'update_logs']
        }),
        ('Links', {
            'classes': ('suit-tab suit-tab-common',),
            'fields': ['custom_depiction', 'c_depiction', 'c_homepage']
        }),
        ('Compatibility', {
            'classes': ('suit-tab suit-tab-common',),
            'fields': ['os_compatibility', 'device_compatibility']
        }),
        # Contact
        ('Maintainer', {
            'classes': ('suit-tab suit-tab-contact',),
            'fields': ['maintainer_name', 'maintainer_email']
        }),
        ('Author', {
            'classes': ('suit-tab suit-tab-contact',),
            'fields': ['author_name', 'author_email']
        }),
        ('Sponsor', {
            'classes': ('suit-tab suit-tab-contact',),
            'fields': ['sponsor_name', 'sponsor_site']
        }),
        # Advanced
        ('Platform', {
            'classes': ('suit-tab suit-tab-advanced',),
            'fields': ['c_architecture', 'c_priority', 'c_essential', 'c_tag']
        }),
        ('Relations', {
            'classes': ('suit-tab suit-tab-advanced',),
            'fields': ['c_depends', 'c_pre_depends', 'c_conflicts', 'c_replaces', 'c_provides']
        }),
        ('Other Relations', {
            'classes': ('suit-tab suit-tab-advanced',),
            'fields': ['c_recommends', 'c_suggests', 'c_breaks']
        }),
        # File System
        ('Storage', {
            'classes': ('suit-tab suit-tab-file-system',),
            'fields': ['storage_', 'c_size', 'c_installed_size']
        }),
        ('Hash', {
            'classes': ('suit-tab suit-tab-file-system',),
            'fields': ['c_md5', 'c_sha1', 'c_sha256', 'c_sha512']
        }),
        # Others
        ('Provider', {
            'classes': ('suit-tab suit-tab-others',),
            'fields': ['c_origin', 'c_source', 'c_bugs', 'c_installer_menu_item']
        }),
        ('Make', {
            'classes': ('suit-tab suit-tab-others',),
            'fields': ['c_build_essential', 'c_built_using', 'c_built_for_profiles']
        }),
        ('Development', {
            'classes': ('suit-tab suit-tab-others',),
            'fields': ['c_multi_arch', 'c_subarchitecture', 'c_kernel_version']
        }),
        ('History', {
            'classes': ('suit-tab suit-tab-statistics',),
            'fields': ['created_at', 'download_times']
        }),
    ]
    suit_form_size = {
        'widgets': {
            'RedactorWidget': apps.SUIT_FORM_SIZE_X_LARGE,
        },
    }
    suit_form_tabs = (
        ('common', 'Common'),
        ('contact', 'Contact'),
        ('advanced', 'Advanced'),
        ('file-system', 'File System'),
        ('others', 'Others'),
        ('statistics', 'Statistics')
    )

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        # field update
        """
        :param change: Boolean
        :param form: VersionForm
        :type obj: Version
        """
        # hash update
        obj.update_hash()
        super(VersionAdmin, self).save_model(request, obj, form, change)
        excluded_column = ['enabled', 'created_at', 'os_compatibility', 'device_compatibility',
                           'update_logs', 'storage', 'c_icon', 'c_md5', 'c_sha1', 'c_sha256', 'c_sha512',
                           'c_size', 'download_times']
        change_list = form.changed_data
        change_num = len(change_list)
        for change_var in change_list:
            if change_var in excluded_column:
                change_num -= 1
        if change is True and change_num > 0:
            obj.update_storage()
            messages.info(request, _("%s storage updating job has been added to the \"high\" queue.") % str(obj))
        else:
            pass
    
    def delete_model(self, request, obj):
        """
        :type obj: Version
        """
        os.unlink(obj.storage.name)
        super(VersionAdmin, self).delete_model(request, obj)

    change_list_template = 'admin/version/change_list.html'
    change_form_template = 'admin/version/change_form.html'
