#Theater One
totalCols1 = 16
totalRows1 = 11
seatCol1 = 5
seatRow1 = 3

#Theater Two
totalCols2 = 1
totalRows2 = 1
seatCol2 = 1
seatRow2 = 1

#Theater Three
totalCols3 = 13
totalRows3 = 6
seatCol3 = 8
seatRow3 = 3


def seats_in_theater(tot_cols, tot_rows, col, row):
    return (tot_cols - (col - 1)) * (tot_rows - row)

print(seats_in_theater(totalCols3, totalRows3, seatCol3, seatRow3))