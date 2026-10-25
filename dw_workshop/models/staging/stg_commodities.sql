with raw_source as (
    select
        "Date" as raw_date,
        "Close" as close_price,
        "Open" as open_price,
        "High" as high_price,
        "Low" as low_price,
        "Volume" as volume,
        symbol
    from {{ source('commodities_dw', 'commodities') }}
),

cleaned as (
    select
        cast(raw_date as date) as trade_date,
        symbol,
        case
            when symbol = 'CL=F' then 'Crude Oil (WTI)'
            when symbol = 'GC=F' then 'Gold'
            when symbol = 'SI=F' then 'Silver'
            else symbol
        end as commodity_name,
        round(cast(open_price as numeric), 4) as open_price,
        round(cast(high_price as numeric), 4) as high_price,
        round(cast(low_price as numeric), 4) as low_price,
        round(cast(close_price as numeric), 4) as close_price,
        coalesce(cast(volume as bigint), 0) as trade_volume
    from raw_source
    where "Close" is not null
)

select * from cleaned
