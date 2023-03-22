    async function statusRequest() {
        let url = SHEET_API_URL + SHEET_KEY
        try {
            let response = await fetch(url)
            if (response.status === 200) {
                let sheet = await response.json()
                return sheet
            }
        } catch(e) {
            console.error('Error fetch status', e);
            await Promise.all([ Promise.resolve(), timeout(15000) ]);
        }

    }

    async function checkStatus() {
        await new Promise(resolve => setTimeout( () => {
            initUpdatePage()
        }, 5000))
    }

    async function getFullSheet() {
        let url = SHEET_API_URL + SHEET_KEY + '?full=1'
        let response = await fetch(url)
        try {
            if (response.status === 200) {
                let sheet = await response.json()
                return sheet
            }
        } catch(e) {
            console.error('Error fetch full info', e);
            await Promise.all([ Promise.resolve(), timeout(15000) ]);
        }
    }

    async function updatePage(){
        let savedValuteSettings = getCookie('valute')
        const sheet = await getFullSheet()
        let currentOrders = []
        let actualOrders = {}
        let orders = sheet.orders
        // defined in template
        TOTAL_USD = sheet.total_usd.toFixed(2)
        TOTAL_RUBLE = sheet.total_ruble.toFixed(2)
        if(savedValuteSettings == 'ruble') {
             total_cost.innerHTML = '₽' + TOTAL_RUBLE
        } else {
             total_cost.innerHTML = '$' + TOTAL_USD
        }
        $('table').find('tr:not(:first-of-type)').each(function(){ if (this.id) {currentOrders.push(Number(this.id))}})

        orders.forEach(function(order){
            let orderIndex = order.order_index

            actualOrders[orderIndex] = order
            let elem = $('table').find(`tr[id=${orderIndex}]`).find('td').each(function(){
                let newValue = order[this.className]
                if (this.innerHTML != newValue) {
                    if (this.className == 'row_index') { this.innerHTML = newValue };
                    if (this.className == 'cost') { this.innerHTML = parseFloat(newValue).toFixed(2) };
                    if (this.className == 'cost_ruble') { this.innerHTML = parseFloat(newValue).toFixed(2) };
                    if (this.className == 'delivery_date') { this.innerHTML = new Date(newValue).toLocaleDateString() }
                    };
            })
        })
        let newOrders = Object.keys(actualOrders).filter(key => !(currentOrders.includes(Number(key))))
                                 .reduce((cur, key) => {return Object.assign(cur, { [key]: actualOrders[key]})}, {});
        let deletedOrders = currentOrders.filter(id => !(Object.keys(actualOrders).includes(id.toString())))
        deletedOrders.forEach(function(id){
            $('table').find(`tr[id=${id}]`).remove()
        })
        Object.keys(newOrders).forEach(function(id){
            order = newOrders[id]
            let clone = $($('template').html());
            clone.attr('id', order.order_index)
            clone.children('.row_index')[0].innerHTML = order.row_index
            clone.children('.order_index')[0].innerHTML = order.order_index
            clone.children('.cost')[0].innerHTML = order.cost
            clone.children('.cost_ruble')[0].innerHTML = order.cost_ruble
            clone.children('.delivery_date')[0].innerHTML = new Date(order.delivery_date).toLocaleDateString()
            $('tbody').append(clone)
        })

        $('tbody').find('tr:not(:first-of-type').sort(function(a, b) {
            return parseInt($('td:first',a).text()) - parseInt($('td:first',b).text())
        }).appendTo($('tbody'));
   }

    async function updateData(lastMD5) {
        const { md5 } = await statusRequest();
        if ($('table').length == 0){
            await Promise.all([ location.reload(), timeout(2000) ]);
        }
        if (lastMD5 != md5) {
            await updatePage();
        }

        return md5;
    }

    function getCookie(name) {
          let matches = document.cookie.match(new RegExp(
            "(?:^|; )" + name.replace(/([\.$?*|{}\(\)\[\]\\\/\+^])/g, '\\$1') + "=([^;]*)"
          ));
          return matches ? decodeURIComponent(matches[1]) : undefined;
    }

    function init_valute() {
        let savedValuteSettings = getCookie('valute')
        if (savedValuteSettings == undefined) {
            document.cookie = "valute=usd"
            savedValuteSettings = getCookie('valute')
        }
        let valuteLetter
        if (savedValuteSettings == 'usd') {
            let valute_sign = '$'
            settings.innerHTML = valute_sign
            if (parseFloat(TOTAL_USD)) {
                total_cost.innerHTML = valute_sign + TOTAL_USD
            }
        } else {
            let valute_sign = '₽'
            settings.innerHTML = valute_sign
            if (parseFloat(TOTAL_RUBLE)) {
                total_cost.innerHTML = valute_sign + TOTAL_RUBLE
            }
        }
        if (!total_cost.innerHTML) {
            total_cost.innerHTML = 'Wait'
        }
    }

    async function changeValute() {
        let saved_valute_settings = getCookie('valute')

        if (saved_valute_settings == 'usd'){
            document.cookie = "valute=ruble"
            settings.innerHTML = '₽'
            total_cost.innerHTML = '₽' + TOTAL_RUBLE
        }
        else{
            document.cookie = "valute=usd"
            settings.innerHTML = '$'
            total_cost.innerHTML = '$' + TOTAL_USD
        }
    }

    function timeout(ms) {
        return new Promise(resolve => { setTimeout(resolve, ms); });
    }

    async function runUpdateTask() {
        let lastMD5 = null;
        while(true) {
            try {
                const [md5] = await Promise.all([ updateData(lastMD5), timeout(2000) ]);
                lastMD5 = md5;
            } catch(e) {
                console.info('Something went wrong', e);
                await Promise.all([Promise.resolve(), timeout(2000) ]);
            }
        }
    }

window.addEventListener('DOMContentLoaded', () => init_valute());
window.addEventListener('DOMContentLoaded', () => settings.addEventListener( "click" , () => changeValute()));
window.addEventListener('DOMContentLoaded', () => runUpdateTask());




