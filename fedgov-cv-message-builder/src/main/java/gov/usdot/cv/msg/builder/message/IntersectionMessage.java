package gov.usdot.cv.msg.builder.message;
import jakarta.xml.bind.annotation.XmlRootElement;

@XmlRootElement
public class IntersectionMessage extends SemiMessage {
	public static long intersectionSitDataDep = 162;
	public static String simpleName = "MAP";//"intersectionSitDataDep"
	public IntersectionMessage() {
		super(intersectionSitDataDep, simpleName);
	}

}
