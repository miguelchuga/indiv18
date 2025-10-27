# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in root directory
##############################################################################
from base64 import standard_b64decode
from PyPDF2 import PdfFileWriter, PdfFileReader
import tempfile
import io
import zipfile
from py3o.template import Template
from subprocess import Popen, PIPE
import re
import os

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval, time
from odoo.tools.misc import find_in_path, ustr
from odoo.exceptions import UserError, AccessError, ValidationError
from .helper import extra_global_vals
from odoo.tools import config, parse_version

import logging

_logger = logging.getLogger(__name__)


MIME_DICT = {
    "odt": "application/vnd.oasis.opendocument.text",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "rtf": "application/rtf",
    "zip": "application/zip"
}

OUTPUT_FILE = [("pdf", "pdf"),
         ("ods", "ods"),
         ("doc", "doc"),
         ("rtf", "rtf"),
         ("docx", "docx")]

def _get_unoconv_bin():
    try:
        return find_in_path('unoconv')
    except IOError:
        return 'unoconv'

# Check the presence of unoconv and return its version at Odoo start-up
unoconv_state = 'install'
unoconv_dpi_zoom_ratio = False
try:
    process = Popen(
        [_get_unoconv_bin(), '--version'], stdout=PIPE, stderr=PIPE
    )
except (OSError, IOError):
    _logger.info('You need unoconv to print a pdf version of the reports.')
else:  
    _logger.info('Will use the unoconv binary at %s' % _get_unoconv_bin())
    out, err = process.communicate()   
    match = re.search(b'([0-9.]+)', out)
    if match:
        version = match.group(0).decode('ascii')
        if parse_version(version) < parse_version('0.7'):
            _logger.info('Upgrade unoconv to (at least) 0.7')
            unoconv_state = 'upgrade'
        else:
            unoconv_state = 'ok'
        if parse_version(version) >= parse_version('0.12.2'):
            unoconv_dpi_zoom_ratio = True

        if config['workers'] == 1:
            _logger.info('You need to start Odoo with at least two workers to print a pdf version of the reports.')
            unoconv_state = 'workers'
    else:
        _logger.info('unoconv seems to be broken.')
        unoconv_state = 'broken'

def _run_unoconv(cmd):
    try:
        # Con la opción -v para obtener más detalles sobre lo que está pasando.
        # unoconv -v -f pdf /tmp/demo.odt /tmp/aei.odt
        # unoconv -f pdf /tmp/demo.odt
        process = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        pdf_content, err = process.communicate()

        if process.returncode not in [0, 1]:
            if process.returncode == -11:
                message = _(
                    'unoconv failed (error code: %s). Memory limit too low or maximum file number of subprocess reached. Message : %s',
                    process.returncode,
                    err[-1000:],
                )
            else:
                message = _(
                    'unoconv failed (error code: %s). Message: %s',
                    process.returncode,
                    err[-1000:],
                )
            _logger.warning(message)
            raise UserError(message)
        else:
            if err:
                _logger.warning('unoconv: %s' % err)
    except:
        raise

    return pdf_content

def get_command(format_out, file_convert):
    # Ejecutar unoconv como un Servicio en Modo Servidor
    # (Whit root) # libreoffice --headless --accept="socket,host=127.0.0.1,port=2002;urp;StarOffice.ServiceManager" &
    # return [_get_unoconv_bin(), "--stdout", "-f", "%s" % format_out, "-p", "2002", "%s" % file_convert]
    return [_get_unoconv_bin(), "--stdout", "-f", "%s" % format_out, "%s" % file_convert]


class BFExtend(models.AbstractModel):
    _name = 'bf.extend'
    _description = 'BF Extend'

    template_odt_id = fields.Many2one("ir.attachment", "Template *.odt", domain=[('type', '=', 'binary')])
    template_output_extension = fields.Selection(
        OUTPUT_FILE,
        string="Output extension",
        help='Output extension (Format Default *.odt Output File)'
    )
    template_output_file = fields.Binary(string='Output file')
    template_output_file_name = fields.Char(string='Output file name')
    merge_report = fields.Boolean(string="Merge report")
    report_html = fields.Html(string="HTML")

    def bf_render(self, record=None, tmpl_odt=None, data={}, output_file='odt'):
        # Call from other object context lang
        # with_context(lang=lang).bf_render(params)
        if not tmpl_odt:
            return None, None
        datas = dict()
        if record:
            datas.update({"o": record})
        datas.update({"data": data})
        datas.update(extra_global_vals(self.env))
        in_stream = io.BytesIO(standard_b64decode(tmpl_odt))
        temp = tempfile.NamedTemporaryFile()
        t = Template(in_stream, temp)
        t.render(datas)
        temp.seek(0)
        default_out_odt = temp.read()
        if output_file == 'odt':
            temp.close()
            return default_out_odt, "odt"
        out = _run_unoconv(get_command(output_file, temp.name))
        temp.close()
        if not out:
            return default_out_odt, "odt"
        return out, output_file
    
    def list_pdf(self):
        # Return list pdfs
        out, output_file = self.bf_render(record=self, tmpl_odt=self.template_odt_id.datas, output_file='pdf')
        if out:
            if output_file == 'pdf':
                pdf_content_stream = io.BytesIO(out)
                return [pdf_content_stream]
        return []


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    report_libreoffice = fields.Boolean(string="Report libreoffice")
    template_id = fields.Many2one("ir.attachment", "Template *.odt")
    output_file = fields.Selection(
        OUTPUT_FILE,
        string="Format Output File.",
        help='Format Output File. (Format Default *.odt Output File)'
    )
    url_theme_screenshot = fields.Char(string='URL theme screenshot')
    merge_pdf = fields.Boolean(string='Merge pdf', help='Merge pdf with template_odt_id')
    merge_template_id = fields.Many2one(
        "ir.actions.report", string='Merge template qweb-pdf', help='Merge template type qweb-pdf')
    rotates_page = fields.Selection(
        [('clockwise', 'Clockwise'), ('counter_clockwise', 'Counter clockwise')], string='Rotates page', default='clockwise')
    angle_rotate_page = fields.Selection(
        [('90', '90'), ('180', '180'), ('270', '270')], string='Angle to rotate the page', help='Angle to rotate the page. Must be an increment of 90 deg.')
    report_multi = fields.Boolean(string='Report multi', help='Multi records in the same report template')
    sidebar_action_id = fields.Many2one(
        'ir.actions.act_window', 'Sidebar action', copy=False,
        help="Sidebar action to make this template available on records "
             "of the related document model")
    filtered_domain_template_ids = fields.One2many('filtered.domain.template', 'report_id', string='Filtered domain template')

    def action_create_sidebar_action(self):
        # sms/models/sms_template.py (ActWindow.create)
        ActWindow = self.env['ir.actions.act_window']
        view = self.env.ref('report_extend_bf.preview_wizard_view_form')

        for report in self:
            button_name = _('Preview (%s)') % report.name
            action = ActWindow.create({
                'name': button_name,
                'type': 'ir.actions.act_window',
                'res_model': 'preview.wizard',
                'context': "{'default_report_id' : %d, 'default_res_ids': active_ids, 'default_res_id': active_id}" % (report.id),
                'view_mode': 'form',
                'view_id': view.id,
                'target': 'new',
                'binding_model_id': report.model_id.id,
            })
            report.write({'sidebar_action_id': action.id})
        return True
    
    def action_unlink_sidebar_action(self):
        for report in self:
            if report.sidebar_action_id:
                report.sidebar_action_id.unlink()
        return True
    
    def unlink(self):
        for report in self:
            if report.sidebar_action_id:
                report.sidebar_action_id.unlink()
        return super(IrActionsReport, self).unlink()

    def unlink_action(self):
        self.action_unlink_sidebar_action()
        return super().unlink_action()

    @api.onchange('report_libreoffice')
    def _onchange_report_libreoffice(self):
        if self.report_libreoffice:
            self.report_type = 'qweb-pdf'

    @api.model
    def _render(self, report_ref, res_ids, data=None):
        report = self._get_report(report_ref)
        if report.report_libreoffice:
            mimetype, out, report_name, ext = self.render_any_docs(report_ref, res_ids, data=data)
            return out, ext
        else:
            return super(IrActionsReport, self)._render(report_ref, res_ids, data)

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        report_sudo = self._get_report(report_ref)
        if report_sudo.report_libreoffice:
            if not data:
                data = {}
            mimetype, out, report_name, ext = self.render_any_docs(report_ref, res_ids, data=data)
            return out, ext
        return super(IrActionsReport, self)._render_qweb_pdf(report_ref, res_ids, data)

    def _postprocess_pdf_report(self, record, buffer):
        attachment_name = safe_eval(self.attachment, {'object': record, 'time': time})
        if not attachment_name:
            return None
        attachment_vals = {
            'name': attachment_name,
            'raw': buffer.getvalue(),
            'res_model': self.model,
            'res_id': record.id,
            'type': 'binary',
        }
        try:
            self.env['ir.attachment'].create(attachment_vals)
        except AccessError:
            _logger.info("Cannot save PDF report %r as attachment", attachment_vals['name'])
        else:
            _logger.info('The PDF document %s is now saved in the database', attachment_vals['name'])
        return buffer

    def render_any_docs(self, report_ref, res_ids=None, data=None):
        if not data:
            data = {}
        docids = res_ids
        report_sudo = self._get_report(report_ref)
        report_obj = self.env[report_sudo.model]
        output_file = report_sudo.output_file
        docs = report_obj.browse(docids)
        report_name = report_sudo.name
        zip_filename = report_name
        if report_sudo.print_report_name and not len(docs) > 1:
            report_name = safe_eval(report_sudo.print_report_name, {'object': docs, 'time': time})
        in_stream = io.BytesIO(standard_b64decode(report_sudo.template_id.datas))
        # Render tmpl easy
        # in_stream = odoo.modules.get_module_resource('report_extend_bf_examples', 'templates', "context_data.odt")
        if not in_stream:
            raise ValidationError('File template not found.')
        temp = tempfile.NamedTemporaryFile()

        def close_streams(streams):
            for stream in streams:
                try:
                    stream.close()
                except Exception:
                    pass
        
        def merge_pdfs(streamsx):
            # Build the final pdf.
            writer = PdfFileWriter()
            for stream in streamsx:
                reader = PdfFileReader(stream)
                # Rotate all pages
                if report_sudo.rotates_page and report_sudo.angle_rotate_page:
                    for pagenum in range(reader.numPages):
                        page = reader.getPage(pagenum)
                        OrientationDegrees = page.get('/Rotate')
                        if not OrientationDegrees:
                            if report_sudo.rotates_page == 'clockwise':
                                page.rotateClockwise(int(report_sudo.angle_rotate_page))
                            else:
                                page.rotateCounterClockwise(int(report_sudo.angle_rotate_page))
                writer.appendPagesFromReader(reader)
            result_stream = io.BytesIO()
            streamsx.append(result_stream)
            writer.write(result_stream)
            result = result_stream.getvalue()
            # We have to close the streams after PdfFileWriter's call to write()
            close_streams(streamsx)
            return result

        def postprocess_report(report, record, buffer):
            if report.attachment:
                attachment_id = report.retrieve_attachment(record)
                if not attachment_id:
                    report._postprocess_pdf_report(record, buffer)

        if not docids:
            datas = {"data": data}
            if 'lang' in data:
                datas.update(extra_global_vals(self.env(context=dict(self.env.context, lang=data.get('lang')))))
            else:
                datas.update(extra_global_vals(self.env))
            t = Template(in_stream, temp)
            records = []
            if 'barcode_records' in datas.get('data', {}):
                for line in datas.get('data').get('barcode_records'):
                    records.append({'o': self.env[line.get('model')].browse(line.get('res_id')), 'qty': line.get('qty')})
                datas.update({'records': records})
            t.render(datas)
            # Mover el puntero de lectura/escritura al inicio del archivo
            temp.seek(0)
            default_out_odt = temp.read()
            if not output_file:
                temp.close()
                return MIME_DICT["odt"], default_out_odt, report_name, "odt"
            out = _run_unoconv(get_command(output_file, temp.name))
            temp.close()
            if not out:
                return MIME_DICT["odt"], default_out_odt, report_name, "odt"
            return MIME_DICT[output_file], out, report_name, output_file

        lang = self.env.user.lang or 'en_US'
        if report_sudo.report_multi:
            if hasattr(report_obj, 'context_lang'):
                lang = docs.context_lang() or lang
            datas = dict(records=docs.with_context(lang=lang))
            datas.update(extra_global_vals(self.env(context=dict(self.env.context, lang=lang))))
            t = Template(in_stream, temp)
            t.render(datas)
            temp.seek(0)
            default_out_odt = temp.read()
            if not output_file:
                temp.close()
                return MIME_DICT["odt"], default_out_odt, report_name, "odt"
            else:
                out = _run_unoconv(get_command(output_file, temp.name))
                if not out:
                    temp.close()
                    return MIME_DICT["odt"], default_out_odt, report_name, "odt"
                else:
                    if output_file == 'pdf':
                        temp.close()
                        return MIME_DICT[output_file], out, report_name, output_file
                    else:
                        temp.close()
                        return MIME_DICT[output_file], out, report_name, output_file
            temp.close()
        else:
            streams = []
            buff = io.BytesIO()
            # This is my zip file
            zip_archive = zipfile.ZipFile(buff, mode='w')
            for doc in docs:
                if hasattr(report_obj, 'context_lang'):
                    lang = doc.context_lang() or lang
                datas = dict(o=doc.with_context(lang=lang))
                datas.update(extra_global_vals(self.env(context=dict(self.env.context, lang=lang))))
                if report_sudo.print_report_name:
                    report_name = safe_eval(report_sudo.print_report_name, {'object': doc, 'time': time})
                    report_name = report_name.replace("/", "_")
                # The custom_report method must return a dictionary
                # If any model has method custom_report
                if hasattr(report_obj, 'custom_report'):
                    datas.update({"data": doc.with_context(lang=lang).custom_report()})

                t = None
                template_ok = False
                if not report_sudo.report_multi:
                    for filtered in report_sudo.filtered_domain_template_ids.sorted(key=lambda r: r.sequence):
                        if doc.filtered_domain(safe_eval(filtered.domain)):
                            t = Template(io.BytesIO(standard_b64decode(filtered.template_id.datas)), temp)
                            template_ok = True
                            break
                if not template_ok:
                    t = Template(in_stream, temp)
                t.render(datas)
                temp.seek(0)
                default_out_odt = temp.read()
                if not output_file:
                    postprocess_report(report_sudo, doc, io.BytesIO(default_out_odt))
                    if len(docids) == 1:
                        temp.close()
                        return MIME_DICT["odt"], default_out_odt, report_name, "odt"
                    else:
                        zip_archive.writestr("%s.odt" % (report_name), default_out_odt)
                else:
                    out = _run_unoconv(get_command(output_file, temp.name))
                    if not out:
                        postprocess_report(report_sudo, doc, io.BytesIO(default_out_odt))
                        if len(docids) == 1:
                            temp.close()
                            return MIME_DICT["odt"], default_out_odt, report_name, "odt"
                        else:
                            zip_archive.writestr("%s.odt" % (report_name), default_out_odt)
                    else:
                        content_stream = io.BytesIO(out)
                        if output_file == 'pdf':
                            streams_record = [content_stream]
                            if report_sudo.merge_pdf:
                                if hasattr(doc, 'list_pdf'):
                                    list_pdf = doc.with_context(lang=lang).list_pdf()
                                    streams_record += list_pdf
                            if report_sudo.merge_template_id:
                                if hasattr(doc, 'merge_report'):
                                    if doc.merge_report:
                                        pdf_content, ext = self._render_qweb_pdf(report_sudo.merge_template_id.report_name, doc.id)
                                        streams_record.append(io.BytesIO(pdf_content))
                                else:
                                    pdf_content, ext = self._render_qweb_pdf(report_sudo.merge_template_id.report_name, doc.id)
                                    streams_record.append(io.BytesIO(pdf_content))
                            result = merge_pdfs(streams_record)
                            streams.append(io.BytesIO(result))
                            postprocess_report(report_sudo, doc, io.BytesIO(result))
                            if len(docids) == 1:
                                temp.close()
                                return MIME_DICT[output_file], result, report_name, output_file
                        else:
                            postprocess_report(report_sudo, doc, content_stream)
                            if len(docids) == 1:
                                temp.close()
                                return MIME_DICT[output_file], out, report_name, output_file
                            else:
                                zip_archive.writestr("%s.%s" % (report_name, output_file), out)
            temp.close()

            if streams:
                result = merge_pdfs(streams)
                return MIME_DICT[output_file], result, zip_filename, output_file
            else:
                # You can visualize the structure of the zip with this command
                # print zip_archive.printdir()
                zip_archive.close()
                return MIME_DICT["zip"], buff.getvalue(), zip_filename, "zip"


class FilteredDomainTemplate(models.Model):
    _name = 'filtered.domain.template'
    _description = 'Filtered domain template'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(default=1)
    domain = fields.Char(string='Domain', required=True)
    template_id = fields.Many2one(
        "ir.attachment", "Template *.odt", required=True)
    report_id = fields.Many2one("ir.actions.report", "Report")
    model = fields.Char(related="report_id.model", string='Model')