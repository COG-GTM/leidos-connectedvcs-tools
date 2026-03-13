package gov.usdot.cv.msg.builder.message;

import jakarta.xml.bind.annotation.XmlRootElement;

@XmlRootElement
public class TravelerInformationMessage extends SemiMessage {
	
	public TravelerInformationMessage() {
		super(2, TravelerInformationMessage.class.getSimpleName());
	}

}
