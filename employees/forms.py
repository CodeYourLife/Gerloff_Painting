# forms.py
from django import forms
from .models import RespiratorClearance

# class RespiratorSection3Form(forms.ModelForm):
#     class Meta:
#         model = RespiratorClearance
#         fields = [
#             'heart_problems',
#             'heart_problems_details',
#             'heart_difficulty_explaining',
#             'other_heart_symptoms',
#             'chest_pain_exercise',
#             'fainting_dizziness',
#             'high_blood_pressure',
#             'irregular_heartbeat',
#         ]
#         labels = {
#             'heart_problems':'Do you have heart problems?',
#             'heart_difficulty_explaining':'Please explain',
#             'chest_pain_exercise':'Chest Pain During Exercise?',
#             'fainting_dizziness':'Fainting or Dizziness?',
#         }
#         # labels = {
#         #     'heart_problems':'Do you have heart problems?',
#         #     'heart_problems_details',
#         #     'heart_difficulty_explaining',
#         #     'other_heart_symptoms',
#         #     'chest_pain_exercise',
#         #     'fainting_dizziness',
#         #     'high_blood_pressure',
#         #     'irregular_heartbeat',
#         # }
#
# class RespiratorSection4Form(forms.ModelForm):
#     class Meta:
#         model = RespiratorClearance
#         fields = ['vision_problems', 'hearing_problems','vision_problems_explained', 'hearing_problems_explained']
#         labels = {
#             'vision_problems_explained':'Please explain your vision problems',
#             'hearing_problems_explained':'Please explain your hearing problems'
#         }
# class RespiratorSection5Form(forms.ModelForm):
#     class Meta:
#         model = RespiratorClearance
#         fields = ['physical_limitation',
#     'fit_test_experience',
#     'difficulty_donning',
#     'difficulty_donning_explanation',
#     'claustrophobia',
#     'claustrophobia_explanation',
#     'additional_comments', ]
#
# class RespiratorSection6Form(forms.ModelForm):
#     class Meta:
#         model = RespiratorClearance
#         fields = ['skin_irritation','rash','anxiety','general_weakness','fatigue','other_symptoms','additional_comments',]
#
#         skin_irritation = models.BooleanField(null=True)
#         rash = models.BooleanField(null=True)
#         anxiety = models.BooleanField(null=True)
#         general_weakness = models.BooleanField(null=True)
#         fatigue = models.BooleanField(null=True)
#         other_symptoms = models.TextField(blank=True, null=True)
#         additional_comments = models.TextField(blank=True, null=True)
#         date_submitted = models.DateTimeField(auto_now_add=True)
#
