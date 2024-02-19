using System.Net;
using System.Net.Mail;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Infra.Email
{
    public class SendEmail : ISendEmail
    {
        public bool Send()
        {
            MailMessage mail = new MailMessage();
            mail.From = new MailAddress("de@gmail.com");
            mail.To.Add("para@gmail.com"); // para
            mail.Subject = "Teste"; // assunto
            mail.Body = "Testando mensagem de e-mail"; // mensagem

            // em caso de anexos
            mail.Attachments.Add(new Attachment(@"C:\teste.txt"));

            using (var smtp = new SmtpClient("smtp.gmail.com"))
            {
                smtp.EnableSsl = true; // GMail requer SSL
                smtp.Port = 587;       // porta para SSL
                smtp.DeliveryMethod = SmtpDeliveryMethod.Network; // modo de envio
                smtp.UseDefaultCredentials = false; // vamos utilizar credencias especificas

                // seu usuário e senha para autenticação
                smtp.Credentials = new NetworkCredential("suaconta@gmail.com", "sua senha");

                // envia o e-mail
                smtp.Send(mail);
            }

            return true;
        }
    }
}
