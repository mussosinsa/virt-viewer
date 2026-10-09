/*
 * Virt Viewer: A virtual machine console viewer
 *
 * Copyright (C) 2007-2012 Red Hat, Inc.
 * Copyright (C) 2009-2012 Daniel P. Berrange
 * Copyright (C) 2010 Marc-André Lureau
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 * Author: Daniel P. Berrange <berrange@redhat.com>
 */

#include <config.h>
#include <glib/gi18n.h>

#ifdef G_OS_WIN32
#include <windows.h>
#endif

#include "virt-viewer-notebook.h"
#include "virt-viewer-util.h"

struct _VirtViewerNotebook {
    GtkNotebook parent;
    GtkWidget *status;
#ifdef G_OS_WIN32
    guint remote_session_check_id;
    gboolean remote_session_blocked;
#endif
};

G_DEFINE_TYPE(VirtViewerNotebook, virt_viewer_notebook, GTK_TYPE_NOTEBOOK)

#ifdef G_OS_WIN32
static gboolean
virt_viewer_notebook_remote_session_check(gpointer data)
{
    VirtViewerNotebook *self = VIRT_VIEWER_NOTEBOOK(data);
    gboolean remote = GetSystemMetrics(SM_REMOTESESSION) != 0;
    gboolean have_display = gtk_notebook_get_nth_page(GTK_NOTEBOOK(self), 1) != NULL;

    if (!have_display)
        self->remote_session_blocked = FALSE;

    if (remote && have_display &&
        (self->remote_session_blocked ||
         gtk_notebook_get_current_page(GTK_NOTEBOOK(self)) == 1)) {
        self->remote_session_blocked = TRUE;
        gtk_label_set_text(GTK_LABEL(self->status),
                           _("Guest display is blocked in a remote desktop session"));
        gtk_notebook_set_current_page(GTK_NOTEBOOK(self), 0);
    } else if (!remote && self->remote_session_blocked) {
        self->remote_session_blocked = FALSE;
        if (gtk_notebook_get_nth_page(GTK_NOTEBOOK(self), 1) != NULL)
            virt_viewer_notebook_show_display(self);
    }

    return G_SOURCE_CONTINUE;
}
#endif

static void
virt_viewer_notebook_dispose(GObject *object)
{
#ifdef G_OS_WIN32
    VirtViewerNotebook *self = VIRT_VIEWER_NOTEBOOK(object);

    if (self->remote_session_check_id != 0) {
        g_source_remove(self->remote_session_check_id);
        self->remote_session_check_id = 0;
    }
#endif

    G_OBJECT_CLASS(virt_viewer_notebook_parent_class)->dispose(object);
}

static void
virt_viewer_notebook_get_property (GObject *object, guint property_id,
                                   GValue *value G_GNUC_UNUSED, GParamSpec *pspec)
{
    switch (property_id) {
    default:
        G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
    }
}

static void
virt_viewer_notebook_set_property (GObject *object, guint property_id,
                                   const GValue *value G_GNUC_UNUSED, GParamSpec *pspec)
{
    switch (property_id) {
    default:
        G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
    }
}

static void
virt_viewer_notebook_class_init (VirtViewerNotebookClass *klass)
{
    GObjectClass *object_class = G_OBJECT_CLASS (klass);

    object_class->get_property = virt_viewer_notebook_get_property;
    object_class->set_property = virt_viewer_notebook_set_property;
    object_class->dispose = virt_viewer_notebook_dispose;
}

static void
virt_viewer_notebook_init (VirtViewerNotebook *self)
{
    self->status = gtk_label_new("");
    gtk_notebook_set_show_tabs(GTK_NOTEBOOK(self), FALSE);
    gtk_notebook_set_show_border(GTK_NOTEBOOK(self), FALSE);
    gtk_widget_show_all(self->status);
    gtk_notebook_append_page(GTK_NOTEBOOK(self), self->status, NULL);
#ifdef G_OS_WIN32
    self->remote_session_check_id = g_timeout_add(250,
                                                  virt_viewer_notebook_remote_session_check,
                                                  self);
#endif
}

void
virt_viewer_notebook_show_status_va(VirtViewerNotebook *self, const gchar *fmt, va_list args)
{
    gchar *text;

    g_debug("notebook show status %p", self);
    g_return_if_fail(VIRT_VIEWER_IS_NOTEBOOK(self));

    text = g_strdup_vprintf(fmt, args);
    gtk_label_set_text(GTK_LABEL(self->status), text);
    gtk_notebook_set_current_page(GTK_NOTEBOOK(self), 0);
    gtk_widget_show_all(GTK_WIDGET(self));
    g_free(text);
}

void
virt_viewer_notebook_show_status(VirtViewerNotebook *self, const gchar *fmt, ...)
{
    va_list args;

    g_return_if_fail(VIRT_VIEWER_IS_NOTEBOOK(self));

    va_start(args, fmt);
    virt_viewer_notebook_show_status_va(self, fmt, args);
    va_end(args);
}

void
virt_viewer_notebook_show_display(VirtViewerNotebook *self)
{
    GtkWidget *display;

    g_debug("notebook show display %p", self);
    g_return_if_fail(VIRT_VIEWER_IS_NOTEBOOK(self));

#ifdef G_OS_WIN32
    if (GetSystemMetrics(SM_REMOTESESSION) != 0) {
        self->remote_session_blocked = TRUE;
        virt_viewer_notebook_show_status(self, "%s",
                                         _("Guest display is blocked in a remote desktop session"));
        return;
    }
#endif

    display = gtk_notebook_get_nth_page(GTK_NOTEBOOK(self), 1);
    if (display == NULL)
        g_debug("FIXME: showing display although it's not ready yet");
    else
        gtk_widget_grab_focus(display);

    gtk_notebook_set_current_page(GTK_NOTEBOOK(self), 1);
    gtk_widget_show_all(GTK_WIDGET(self));
}

VirtViewerNotebook*
virt_viewer_notebook_new (void)
{
    return g_object_new (VIRT_VIEWER_TYPE_NOTEBOOK, NULL);
}
