Select * from account_bank_statement where 

Select * from account_bank_statement_line where statement_id = 469



Select * from account_bank_statement_line where id = 9194


Select * from account_bank_statement_line where move_id = 2033

Update account_payment set state = 'paid' where id = 2033

select is_reconciled,* from account_payment where id in (2033)

update account_payment set is_matched = true where id =2033

Select statement_line_id,* from account_move where id in (34378,17220)

update account_move set statement_line_id = null where id = 17220


Select  is_matched,date,state,* from account_payment where date <='30-10-2025' and is_matched = False
 
--pagos conciliados que estabamal el cam
update account_payment set is_matched = true   where date <='31-10-2025' and is_matched = False

update account_payment set is_matched = true where id =3236
2033
2481
3236
102
143
175
176
177
179
199
200
227
284
342
343
346
394
408
409
434
457
555
524
579
581
601
690
630
681
691
798
841
843
875
927
949
971
980
991
997
1076
1077
1084
1085
1089
1090
1107
1124
1172
1177
1186
1195
1208
1235
1307
1319
1379
1426
2022
1502
1507
1511
1555
1596
1597
1598
1636
1667
1780
1781
2001
1806
1829
1830
1861
1898
1931
2052
2061
2071
2157
2161
2240
2291
2292
2384
2340
2366
2376
2511
2614
2628
2640
2723
2734
2738
2771
2820
2840
2882
2914
2986
3040
3121
3130
3144
3168
3169
3218
3225
3252
3260
3276
3301
3333
3436
3574
3592
3594
3596
3608
3645
3660
3700
3707
3724
3734
3736
3744
3749
3766
3767
3813
3977
3831
3855
3867
3931
3940
3941
3943
4028
4086
4109
4114
4117
4154
4177
4251
4252
4267
4270
4271
4354
4360
4371
4391