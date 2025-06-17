from __future__ import unicode_literals
from django.utils.safestring import mark_safe

def get_help_text():
    output = """
<h4>On this page you can set or revoke access to a document.</h4>
<p>You can give access to a document either to a single user or a group.</p>
<p><img src="/static/appearance/images/help_edit_acls.png" alt="Radio button info" /></p>
<p>If you give a group access, <strong>every</strong> member of this group will have the same level of access.</p>
<p>There are three access levels:</p>
<ul>
<li><strong>No access</strong>: The user has no access to the document.</li>
<li><strong>Limited access</strong>: The user can view and download the document, but cannot delete it or share it with other users</li>
<li><strong>Full access</strong>: The user can even delete and share this document.</li>
</ul>
<p>For a more detailed description about the permissions included in every level click on the netry ACLs ( Access Control List )</p>
<p>The owner of the document ( the user who uploaded the document ) has always full access.</p>
<p><strong>Special groups:</strong></p>
<ul>
<li><strong>All</strong>: Every user of the document system is automatically in this group.</li>
<li><strong>All lawyers</strong>: All lawyers areautomatically in this group.</li>
</ul>
<p>A document a user has not access to might be listed in a search query result. No preview or other ways to access to the document will be available. The user still needs permission by the owner to access this document.</p>
<p>&nbsp;</p>
    """
    return mark_safe(output)
