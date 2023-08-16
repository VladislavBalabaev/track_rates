# Bond screening & analysis
This repository allows to parse all bonds listed on MOEX using [ISS MOEX API](https://iss.moex.com) and to add some financial statistics to each instrument such as: coupon yield, bond yield, dollar duration...

The creation of this repository was initially inspired by section **4.7 Determining zero rates** of the book [Options, Futures, and Other Derivatives](https://www.amazon.com/Options-Futures-Other-Derivatives-9th/dp/0133456315) using system of equations on bonds that were viewed as sum cash flows.  

The result of such process allows to produce chart showing the zero rate as a function of maturity is known as the **zero curve** (*check [explore.ipynb](https://github.com/VladislavBalabaev/track_rates/blob/master/explore.ipynb)*).