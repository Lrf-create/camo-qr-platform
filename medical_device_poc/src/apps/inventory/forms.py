from __future__ import annotations

import uuid

from django import forms

from apps.inventory.models import InstrumentBox, InstrumentType


class InstrumentTypeForm(forms.ModelForm):
    class Meta:
        model = InstrumentType
        fields = ["type_code", "display_name"]
        labels = {
            "type_code": "TYPE",
            "display_name": "名称",
        }

    def clean_type_code(self) -> str:
        value = self.cleaned_data["type_code"].strip().upper()
        if not value:
            raise forms.ValidationError("TYPE 不能为空。")
        return value


class InstrumentBoxForm(forms.ModelForm):
    class Meta:
        model = InstrumentBox
        fields = ["box_code", "box_name"]
        labels = {
            "box_code": "框编号",
            "box_name": "名称",
        }

    def clean_box_code(self) -> str:
        value = self.cleaned_data["box_code"].strip().upper()
        if not value:
            raise forms.ValidationError("框编号不能为空。")
        return value

    def save(self, commit: bool = True):
        box = super().save(commit=False)
        if not box.qr_token:
            box.qr_token = uuid.uuid4()
        if commit:
            box.save()
            self.save_m2m()
        return box
