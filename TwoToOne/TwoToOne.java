public class TwoToOne {

    static String str1 = "loopingisfunbutdangerous";
    static String str2 = "lessdangerousthancoding";
    
    public static String longest(String s1, String s2) {
        int s1Len = s1.length;
        int s2Len = s2.length;
        int i = 1;
        int j = 0;

        String longestLen = s1Len > s2Len ? s1 : s2;
        String[] arr = longestLen.split("");

        while(i < arr.length) {
            if(arr[i] == arr[j]) {
                i++;
            } else {
                j++;
                arr[j] = arr[i];
                i++;
            }
        }
        return j + 1;
        
    }

    public static void main(String[] args) {
        longest(TwoToOne.srt1, TwoToOne.str2);
    }
}