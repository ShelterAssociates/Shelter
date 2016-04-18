from django import forms
from .models import City,Survey
import urllib2,urllib
import json
import simplejson 



SURVEYTYPE_CHOICES = (('survey_type', 'Rapid Appraisal'),
                      ('survey_type', 'Rapid Household Survey'),
                      ('survey_type', 'Social Economic'))

class SurveyCreateForm(forms.ModelForm): 
    kobotoolSurvey_id = forms.ChoiceField(widget=forms.Select(),required=True)
    kobotoolSurvey_url = forms.CharField(required=True)    
    def __init__(self,*args,**kwargs):
        super(SurveyCreateForm,self).__init__(*args,**kwargs)
        list_i=[]
        list_i=getKoboIdList()   
        self.fields['kobotoolSurvey_id'].choices=list_i
        self.fields['kobotoolSurvey_id'].initial=[0]
        self.fields['kobotoolSurvey_url'].widget.attrs['readonly'] = True 
    class Meta:
        model=Survey
        fields = ['Name','Description','City_id','Survey_type','AnalysisThreshold','kobotoolSurvey_id']
     
     def clean_foo(self):
        data = self.cleaned_data.get('kobotoolSurvey_id')
        print "***"
        print data
        if data == self.fields['kobotoolSurvey_id'].choices[0][0]:
            raise forms.ValidationError('This field is required')
        return data 
       
        
def getKoboIdList():
    url="http://kc.shelter-associates.org/api/v1/forms?format=json"   
    req = urllib2.Request(url)
    req.add_header('Authorization', 'OAuth2 a0028f740988d80cbe670f24a9456d655b8dd419')
    resp = urllib2.urlopen(req)
    content = resp.read()         
    data = json.loads(content) 
    
    temp_arr=[]
    temp_arr.append(('------------','-----------'))
    for value in data:  
        survey_list={}
        survey_list['id']= value['id_string']
        survey_list['value']=value['url']
        temp_arr.append((value['id_string'],value['id_string']))            
      
    return temp_arr        