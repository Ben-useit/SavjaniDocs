from __future__ import unicode_literals

import logging

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from common.settings import setting_project_url
from mailer.tasks import task_send
from .models import AccessControlList

logger = logging.getLogger(__name__)

def task_add_full_permision(document, user):
    Role = apps.get_model(
        app_label='permissions', model_name='Role'
    )
    if not user.is_superuser:
        role = None
        try:
            role = Role.objects.get(label=user.first_name+" "+user.last_name)
        except Role.DoesNotExist:
            logger.error("There is NO role with the same %s", cls.user.username)
        
        if role:
            acl = AccessControlList.objects.create(
               object_id=document.pk,content_type=ContentType.objects.get_for_model(document), role=role
            )    
            acl.add_full_doc_permissions()    
    
def task_send_mail(permission_holder,user,document,granted):
        UserMailer = apps.get_model(
            app_label='mailer', model_name='UserMailer'
        )
        user_mailer = UserMailer.objects.get(default=True)
        
        #user who wants permission
        username = permission_holder.first_name+" "+permission_holder.last_name
        reply_to = permission_holder.email
        
        if granted:
        
            subject = "EDMSDocs: Permission granted"
            body ="""
            <body lang="en-US" link="#AE132D" vlink="#AE132D" dir="ltr">
            <div style="padding:10px;">
            <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
            <font color="#000000"><font face="Calibri">"""
            body += str(username)
            body += """ has granted you permission for the following document:</font></font></font></p>
            <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
            <font color="#000000"><font face="Calibri">"""
            body += """ <a href=" """ 
             
            body+= str(setting_project_url.value)+"/documents/"+str(document.id)+"/preview/"
            body += """ " style="color:#AE132D;">"""
            body += str(document)
            body += """
            </a></font></font></font></p><hr/>

            <p><span style="font-variant: normal"><font color="#000000"><font face="Calibri"><span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">*
            Please do not reply to this email. Your response will not be
            received.<br/>
            </span></span></span></font></font></font></span>"""
            if reply_to:
                body +="""
                <span style="font-variant: normal">
                <font color="#000000"><font face="Calibri">
                <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">
                </span></span></span></font></font></font></span><span style="font-variant: normal">
                <font color="#000000"><font face="Calibri">
                <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">Contact:
                <a href="mailto:"""
                body += reply_to
                body += """ " style="color:#AE132D;">"""
                body += reply_to
                body += """</a></span></span></span></font></font></font></span></p>"""
            body +="""</div>
            <p><img src="https://www.useit-mw.com/docs96x96.png" name="docs" width=60 height=60 align="middle" border="0"/>

            <font face="Calibri"><b>EDMSDocs</b></font></p></body>
            """
        else:
            subject = "EDMSDocs: Permission denied"
            body ="""
            <body lang="en-US" link="#AE132D" vlink="#AE132D" dir="ltr">
            <div style="padding:10px;">
            <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
            <font color="#000000"><font face="Calibri">"""
            body += str(username)
            body += """ has denied permission for the following document:</font></font></font></p>
            <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
            <font color="#000000"><font face="Calibri">"""
            body += str(document) 
            body += """
            </font></font></font></p><hr/>

            <p><span style="font-variant: normal"><font color="#000000"><font face="Calibri"><span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">*
            Please do not reply to this email. Your response will not be
            received.<br/>
            </span></span></span></font></font></font></span>"""
            if reply_to:
                body +="""
                <span style="font-variant: normal">
                <font color="#000000"><font face="Calibri">
                <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">
                </span></span></span></font></font></font></span><span style="font-variant: normal">
                <font color="#000000"><font face="Calibri">
                <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">Contact:
                <a href="mailto:"""
                body += reply_to
                body += """ " style="color:#AE132D;">"""
                body += reply_to
                body += """</a></span></span></span></font></font></font></span></p>"""
            body +="""</div>
            <p><img src="https://www.useit-mw.com/docs96x96.png" name="docs" width=60 height=60 align="middle" border="0"/>

            <font face="Calibri"><b>EDMSDocs</b></font></p></body>
            """            
        task_send.apply_async(
            kwargs={
                'as_attachment': False,
                'body': body,
                'document_id': None,
                'recipient': user.email,
                'sender': "",
                'subject': subject,
                'user_mailer_id': user_mailer.id,
            }
        )    

def task_get_role_context(request,object_id):
    Role = apps.get_model(
        app_label='permissions', model_name='Role'
    )
    object_content_type = get_object_or_404(
        ContentType, app_label='documents',
        model='document'
    )  
    StoredPermission = apps.get_model(
        app_label='permissions', model_name='StoredPermission'
    )
    current_roles_rw = []
    current_roles_ro = []
    if object_id:
        acl = AccessControlList.objects.filter(
                content_type=object_content_type,
                object_id=object_id
            )
        sp = StoredPermission.objects.get(name='acl_edit')
         
        for item in acl:
            if sp in item.permissions.all():
                   current_roles_rw.append(item.role)
            else:
                current_roles_ro.append(item.role)
                
    user = request.user.first_name+" "+request.user.last_name
    lawyers = Role.objects.filter(role_type='Lawyer').exclude(label=user)
    lawyers_list = []
    for l in lawyers:
        if l in current_roles_rw:
            lawyers_list.append((l,2))
        elif l in current_roles_ro:
            lawyers_list.append((l,1))            
        else:
            lawyers_list.append((l,0))
             
    others = Role.objects.filter(role_type='Other').exclude(label=user)
    others_list = []
    for l in others:
        if l in current_roles_rw:
            others_list.append((l,2))
        elif l in current_roles_ro:
            others_list.append((l,1))            
        else:
            others_list.append((l,0))
    
    
    all_roles = Role.objects.filter(role_type='Group')
    group_roles=[]
    for r in all_roles:
        if r.label == 'All Lawyers' or r.label == 'All':
            if r in current_roles_rw:
                group_roles.append((r,[],2))
            elif r in current_roles_ro:    
                group_roles.append((r,[],1))
            else:
                group_roles.append((r,[],0))
        else:
            groups = []
            for g in r.groups.iterator():
                groups.append(g.name)
            if r in current_roles_rw:
                group_roles.append((r,groups,2))
            elif r in current_roles_ro:    
                group_roles.append((r,groups,1))
            else:
                group_roles.append((r,groups,0))
               
    return  { 'groups':group_roles, 'lawyers': lawyers_list,'others':others_list}
    
