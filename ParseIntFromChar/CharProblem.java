    class CharProblem {

    private static String age1 = "4 years old";
    private static String age2 = "5 years old";
    private static String age3 = "9 years old";
    private static String age4 = "1 years old";

    public static void main(String[] args) {
        System.out.println(howOld(age1));
    }

    public static int howOld(final String herOld) {

        return Integer.parseInt(herOld.replaceAll("\\D+", ""));
    }
}