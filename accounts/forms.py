from django import forms


from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from django.contrib.auth.models import User
from django.forms.widgets import TextInput,PasswordInput

#For Signup
class CreateUserForm(UserCreationForm):
    class Meta:
        model = User
        fields= ['username','email','password1','password2']

    def __init__(self, *args, **kwargs):
        super(CreateUserForm, self).__init__(*args, **kwargs)
        placeholders = {
            'username': 'Enter your username',
            'email': 'Enter your email',
            'password1': 'Create a password',
            'password2': 'Confirm your password'
        }
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': placeholders.get(field, '')
            })
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered..")
        return email
            
#For Signin
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget = TextInput(attrs={'class':'form-control','placeholder':'Username'})
        )
    password = forms.CharField(
        widget=PasswordInput(attrs={'class':'form-control','placeholder':'password'})
    )


    
