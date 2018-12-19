// attempt 1
import java.util.LinkedHashSet;
import java.util.Arrays;
import java.util.Collections;

class TwoToOne1 {
    static String str1 = "loopingisfunbutdangerous";
    static String str2 = "lessdangerousthancoding";

    public static LinkedHashSet<String> longest(String s1, String s2) {
        LinkedHashSet<String> set  = new LinkedHashSet<String>();
        
        int s1Len = s1.length();
        int s2Len = s2.length();
        System.out.println(s1Len);
        System.out.println(s2Len);
        String longestLen = s1Len > s2Len ? s1 : s2;
        String[] newStr = longestLen.split("");

        String[] newArr = Collections.sort(newStr);
        
        System.out.println(longestLen);
        for(int i = 0; i < newArr.length; i++)
        {
            set.add(newArr[i]);

        }
        return set;
    }

    public static void main(String[] args) {
        TwoToOne.longest(str1, str2);
    }
}