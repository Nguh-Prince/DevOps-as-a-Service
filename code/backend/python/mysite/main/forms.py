from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Evenement, Instance

class EvenementForm(forms.ModelForm):
    participants_file = forms.FileField(
        required=False,  # Optional file upload
        label=_("Liste des participants (Excel)"),
        widget=forms.FileInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = Evenement
        # fields = '__all__'  # Include all fields
        labels = {
            'nom': _('Nom de l\'événement'),
            'ville': _('Ville'),
            'pays': _('Pays'),
            'lieu': _('Lieu'),
            'nombres_de_places': _('Nombre de places'),
            'rempli': _('Événement complet'),
            'prix': _('Prix d\'entrée'),
            'entree_gratuit': _('Entrée gratuite'),
            'description': _("Description"),
            'categorie': _("Categorie"),
            "type": _("Type"),
            'organisateur': _("Organisateur"),
            "contact": _("Contact d'organisateur (email ou tel)"),
            "date_heure_debut": _("Debut (Date & heure)"),
            "date_heure_fin": _("Fin (Date & heure)"),
            "lieu": _("Lieu"),
            "lien": _("Lien")
        }
        fields = labels.keys()
        textarea = forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
        textinput = forms.TextInput(attrs={'class': 'form-control'})
        numberinput = forms.NumberInput(attrs={'class': 'form-control'})
        checkboxinput = forms.CheckboxInput(attrs={'class': 'form-check-input'})
        datetimefield = forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'})

        widgets = {
            'nom': textinput,
            'lieu': textarea,
            'ville': textinput,
            'pays': textinput,
            'nombres_de_places': numberinput,
            'prix': numberinput,
            'rempli': checkboxinput,
            'entree_gratuit': checkboxinput,

            'organisateur': textinput,
            'contact': textinput,

            'description': textarea,
            'categorie': forms.Select(choices=Evenement.EVENT_CATEGORIES, attrs={'class': 'form-control select'}),
            'type': forms.Select(choices=Evenement.EVENT_TYPES, attrs={'class': 'form-control select'}),

            'date_heure_debut': datetimefield,
            'date_heure_fin': datetimefield,
            'lien': forms.URLInput(attrs={'class': 'form-control'})
        }

    def clean_nombres_de_places(self):
        """Ensure number of places is positive"""
        nombres_de_places = self.cleaned_data.get('nombres_de_places')
        if nombres_de_places is not None and nombres_de_places < 0:
            raise forms.ValidationError(_('Le nombre de places doit être un nombre positif.'))
        return nombres_de_places

    def clean_participants_file(self):
        file = self.cleaned_data.get("participants_file")
        if file:
            if not file.name.endswith((".xls", ".xlsx")):
                raise forms.ValidationError("Le fichier doit être au format Excel (.xls ou .xlsx).")
        return file


class UpdateEvenementForm(EvenementForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            if "attrs" in field.widget.__dict__:
                field.widget.attrs['id'] = f"edit_{field_name}"


class InstanceForm(forms.ModelForm):
    class Meta:
        model = Instance
        labels = {
            "name": _("Nom"),
            "host_port": _("Port"),
            "admin_password": _("Mot de passe root")
        }
        fields = labels.keys()
        
        textinput = forms.TextInput(attrs={'class': 'form-control'})
        numberinput = forms.NumberInput(attrs={'class': 'form-control'})
        
        widgets = {
            'name': textinput,
            "host_port": numberinput,
            "admin_password": textinput
        }