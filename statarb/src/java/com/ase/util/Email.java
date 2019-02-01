package ase.util;

import org.apache.commons.mail.EmailException;
import org.apache.commons.mail.SimpleEmail;

public class Email {

	public static void email(String subject,String message) throws EmailException
	{
		SimpleEmail email=new SimpleEmail();
		email.addTo("ase@tower-research.com");
		email.setFrom("ase@tower-research.com");
		email.setHostName("mail.tower-research.com");
		email.setSubject(subject);
		email.setMsg(message);
		email.send();
	}
	
	public static void main(String[] args) throws EmailException{
		email("This is an email from java","oh, yeah");
	}
}
